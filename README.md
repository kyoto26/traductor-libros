# traductor-docs

## Checklist de seguridad pendiente por fase

Estas tareas quedan documentadas para no perderlas de vista, pero no se implementan todavía — se abordan cuando se llegue a la fase correspondiente.

### Fase 2 (calidad de traducción)

- [ ] Sanitizar cualquier contenido que el usuario ingrese en el glosario o configuración antes de insertarlo en el prompt hacia el LLM, para evitar prompt injection.

### Fase 3 (EPUB)

- [ ] Protección contra "zip bomb": un EPUB es un ZIP, hay que limitar el tamaño total descomprimido antes de extraer todo el contenido.
- [ ] Protección contra "zip slip": validar que ningún nombre de entry dentro del ZIP intente escribir fuera del directorio de extracción (rutas tipo `../../`).

### Fase 4 (PDF)

- [ ] Confirmar que la extracción con PyMuPDF es puramente de lectura pasiva (solo texto), sin ejecutar JavaScript embebido ni contenido interactivo del PDF.
