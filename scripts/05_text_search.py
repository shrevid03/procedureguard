import os, sys, time, requests
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

SEARCH = os.environ["SEARCH_ENDPOINT"].rstrip("/")
KEY = os.environ["SEARCH_ADMIN_KEY"]
API = os.environ.get("SEARCH_API_VERSION", "2024-07-01")
INDEX = os.environ["SEARCH_INDEX_NAME"]
CONN = os.environ["STORAGE_CONNECTION_STRING"]
CONTAINER = os.environ["STORAGE_CONTAINER"]
H = {"Content-Type": "application/json", "api-key": KEY}
DS, IXR = "procedureguard-text-ds", "procedureguard-text-ixr"

def put(kind, name, body):
    r = requests.put(f"{SEARCH}/{kind}/{name}?api-version={API}", headers=H, json=body)
    if r.status_code not in (200,201,204):
        print(f"[ERR] {kind}/{name}: {r.status_code}\n{r.text}"); r.raise_for_status()
    print(f"[ok] {kind}/{name}")

def build():
    put("datasources", DS, {"name":DS,"type":"azureblob",
        "credentials":{"connectionString":CONN},"container":{"name":CONTAINER}})
    put("indexes", INDEX, {"name":INDEX,"fields":[
        {"name":"id","type":"Edm.String","key":True},
        {"name":"content","type":"Edm.String","searchable":True},
        {"name":"metadata_storage_name","type":"Edm.String","searchable":True,"filterable":True}],
        "semantic":{"configurations":[{"name":"sop-sem","prioritizedFields":{
            "prioritizedContentFields":[{"fieldName":"content"}],
            "titleField":{"fieldName":"metadata_storage_name"}}}]}})
    put("indexers", IXR, {"name":IXR,"dataSourceName":DS,"targetIndexName":INDEX,
        "parameters":{"configuration":{"dataToExtract":"contentAndMetadata"}},
        "fieldMappings":[
            {"sourceFieldName":"metadata_storage_path","targetFieldName":"id",
             "mappingFunction":{"name":"base64Encode"}},
            {"sourceFieldName":"metadata_storage_name","targetFieldName":"metadata_storage_name"}]})

def wait():
    url=f"{SEARCH}/indexers/{IXR}/status?api-version={API}"
    print("\n>> Extracting text from the PDF...")
    for _ in range(40):
        last=(requests.get(url,headers=H).json().get("lastResult") or {})
        st=last.get("status","pending")
        print(f"   status={st} processed={last.get('itemsProcessed',0)} failed={last.get('itemsFailed',0)}")
        if st in ("success","transientFailure"):
            for e in last.get("errors",[])[:3]: print("   error:",e.get("errorMessage"))
            return
        time.sleep(10)

def query(q):
    c=SearchClient(SEARCH,INDEX,AzureKeyCredential(KEY))
    print(f"\n=== Search: {q!r} ===")
    try:
        res=list(c.search(search_text=q,query_type="semantic",
                          semantic_configuration_name="sop-sem",top=5))
    except Exception:
        res=list(c.search(search_text=q,top=5))
    if not res: print("   (no matches)")
    for i,r in enumerate(res,1):
        snip=(r.get("content") or "").strip().replace("\n"," ")[:280]
        print(f"\n{i}. {r.get('metadata_storage_name')}  (score {r['@search.score']:.2f})\n   {snip}")

if __name__=="__main__":
    build(); wait(); query(sys.argv[1] if len(sys.argv)>1 else "assembly step")
