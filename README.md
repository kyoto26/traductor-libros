# traductor-docs

## Checklist de seguridad pendiente por fase

Estas tareas quedan documentadas para no perderlas de vista, pero no se implementan todavía — se abordan cuando se llegue a la fase correspondiente.

### Fase 2 (calidad de traducción)

- [ ] Sanitizar cualquier contenido que el usuario ingrese en el glosario o configuración antes de insertarlo en el prompt hacia el LLM, para evitar prompt injection.

### Fase 3 (EPUB)

- [x] Protección contra "zip bomb": un EPUB es un ZIP, hay que limitar el tamaño total descomprimido antes de extraer todo el contenido. Resuelto en `extractors/zip_safety.py`.
- [x] Protección contra "zip slip": validar que ningún nombre de entry dentro del ZIP intente escribir fuera del directorio de extracción (rutas tipo `../../`). Resuelto en `extractors/zip_safety.py`.

### Fase 4 (PDF)

- [ ] Confirmar que la extracción con PyMuPDF es puramente de lectura pasiva (solo texto), sin ejecutar JavaScript embebido ni contenido interactivo del PDF.

## Deuda técnica pendiente por fase

### Fase 2 (calidad de traducción)

- [ ] **Doble formateo de glosario (decisión temporal):** `prompt_builder.build_translation_request()` ya arma el `context` incluyendo las instrucciones de glosario, pero `llm_client._build_system_prompt()` también sabe formatear `glossary` por su cuenta. Por ahora, quien llame a `translate()` después de pasar por `prompt_builder` debe pasar `glossary=None` para no duplicar las instrucciones en el prompt final — es una regla implícita, no algo forzado por el código. Cuando conectemos `routes.py` al flujo real, decidir si vale la pena el refactor: sacar el manejo de `glossary`/`context` de `llm_client.py` y dejar que `prompt_builder.py` sea la única fuente de ese formateo.

### Fase 5 (persistencia)

- [ ] **`Document` con `source_element`/`source_soup` poblados no es serializable tal cual.** Estos campos (agregados en `models/document.py` para que `epub_extractor.py`/`epub_reconstructor.py` puedan ubicar cada bloque de vuelta en su posición original del HTML) guardan objetos de BeautifulSoup, no datos planos — no se pueden volcar directo a JSON/DB para guardar el progreso de un job y reanudarlo después. Cuando implementemos persistencia de jobs, decidir el enfoque: lo más simple es no persistir el `Document` completo, sino reconstruirlo desde el archivo original (el EPUB en disco) en cada resume, guardando solo el progreso de traducción (qué bloques ya se tradujeron y su `translated_text`) como datos planos aparte.
