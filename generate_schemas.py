import json
from pathlib import Path
from fabrik_betriebssystem.modelle import Uebergangskontext
out=Path('schemas'); out.mkdir(exist_ok=True)
schema=Uebergangskontext.model_json_schema()
schema['$id']='https://fabrik-betriebssystem.local/schemata/uebergangskontext/1.0.0'
schema['titel']='Uebergangskontext'
(out/'uebergangskontext-1.0.0.json').write_text(json.dumps(schema,indent=2,ensure_ascii=False),encoding='utf-8')
