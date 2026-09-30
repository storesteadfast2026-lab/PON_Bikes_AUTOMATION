# Update incremental 1001.0900 — base validada 1001.0832

Instalación activa única: `C:\Docker-Projects\PON_Bikes_Automation`.
Este paquete contiene únicamente los dos archivos de aplicación modificados, los launchers y el soporte de actualización. No contiene una instalación alternativa, Docker/config nuevos, modelos ni migraciones nuevos. Debe extraerse fuera de la instalación activa.

## Requisitos previos comprobados antes de modificar la instalación

La última salida proporcionada por el usuario mostró `Test-Path .git = False`. Este paquete NO recupera ni inicializa automáticamente un repositorio perdido. Es necesario restaurar el repositorio original en `C:\Docker-Projects\PON_Bikes_Automation\.git` antes de ejecutar el update.

Git debe tener un HEAD válido y `git status` debe funcionar en esa carpeta. Los archivos `receiving/views.py` y `receiving/tests.py` de la release 1001.0832 deben estar registrados en el commit actual, sin modificaciones pendientes en esos dos archivos. Esto permite que el commit guardado reproduzca el código real anterior al update; no se crea un commit automáticamente. Otros archivos ajenos al update pueden tener cambios pendientes. Se verifican los hashes de ambos archivos contra la base 1001.0832.

Si falta .git, Git es inaccesible, falta HEAD, la base no coincide o alguno de los dos archivos no está versionado/guardado en HEAD, 01 se detiene ANTES de escribir backups o modificar archivos. No se ejecuta git init.

## Aplicación

Abrir PowerShell en la carpeta extraída y ejecutar, deteniéndose ante cualquier error:

```powershell
.\01_PREPARE_INSTALL.ps1
.\02_APPLY_UPDATE.ps1
.\04_VALIDATE.ps1
```

01 comprueba Git y la base, guarda `PRE_UPDATE_COMMIT.txt`, crea `database_before_update.sql` y guarda una copia pequeña de `.env` y la lista de archivos modificados. NO crea un backup `app\`. Registra los datos de recuperación antes de reemplazar código, para permitir rollback incluso si la preparación falla parcialmente. Copia exclusivamente los archivos listados por UPDATE_FILES.txt, en la carpeta activa existente. .git y continuity permanecen en su ubicación. Mantiene el preflight Translogic vigente.

02 mantiene rebuild/recreate Docker y los checks actuales. No permite aplicar una preparación incompleta. No incorpora nuevas migraciones de modelos; sigue usando el estado de la base 1001.0832.

04 exige un repositorio Git accesible, un pre-update commit recuperable, un respaldo PostgreSQL no vacío y ausencia de app\ en el nuevo backup. Valida Django, estado de migraciones, suite completa de 68 tests, lectura real del Product Master configurado en Docker y HTTP de la aplicación. No genera snapshots.

03_ROLLBACK.ps1 restaura únicamente los archivos modificados mediante `git restore --source=<pre-update commit> --staged --worktree`, restaura PostgreSQL y .env, reconstruye/recrea web y ejecuta Django check. No mueve HEAD ni elimina cambios ajenos a esos archivos. No recrea .git, no restaura una copia app\ y no usa docker compose down -v. El rollback solicita la confirmación operacional habitual porque restaura la base de datos anterior.

05_CREATE_CONTINUITY_SNAPSHOT continúa separado y manual, sin cambios.

## PBP → PON y datos históricos

La clasificación original y los valores de importación siguen en ContainerProductStatus, con el esquema ya existente en 1001.0832. Los snapshots válidos no se sobrescriben por un master posterior. Los snapshots PBP incompletos se reparan durante trabajo explícito desde la evidencia conservada del master: CODE, PON_SKU, CODE2, nombres, cubic, weight y dimensiones. El Product Check explícito recupera también decisiones antiguas. Si los valores históricos están disponibles y son válidos, no pide dimensiones/peso manuales.

Group1 conserva el mapping PON existente. Group2 conserva el cálculo actual, incluido CHG02 para cubic > 0.4. Se conserva la selección original NEW/PBP_TO_PON/EXISTING, la fila naranja A:AD y el formato Translogic de 1001.0832. No se modifica Customer Report.

Limitación histórica: si se eliminó el master original y el estado anterior nunca guardó clasificación/datos PBP, esa evidencia no puede reconstruirse con certeza. No se inventan datos ni se interpreta el master posterior como prueba del estado original.

## Lectura rápida del container

El GET /containers/<id>/ lee únicamente las líneas del container y los estados persistidos. No compara las filas del catálogo, no parsea el archivo físico, no reconstruye historia, no escribe estados y no genera New Product Import. La comparación pesada permanece en los puntos explícitos del workflow: sincronización del master, confirmación del recibido y Product Check. El export conserva su compatibilidad de inicialización explícita cuando aún no hay clasificación, y reutiliza el estado guardado en redescargas normales.

La sincronización actualiza los estados de los containers abiertos con recibido confirmado; los containers cerrados conservan su historial. Un estado antiguo incompleto se resuelve al abrir Product Check explícitamente, no al cambiar de container. Se utiliza el JSON histórico existente para guardar una copia de la última clasificación explícita; no hay un modelo ni una arquitectura nuevos.

La lista lateral de 20 containers utiliza dos consultas en lugar de una consulta por container. Se cargan los SourceFile junto con los batches donde corresponde, evitando lecturas repetidas evidentes.

## Validación real realizada aquí

- Django 5.1.15 con SQLite: 68 tests OK (63 existentes + 5 nuevos), 9.713 s.
- Django check: OK.
- makemigrations --check --dry-run: sin diferencias.
- Migraciones de la copia local aplicadas; migrate --check: OK. No se generan migraciones nuevas.
- Servidor local SQLite en 127.0.0.1:8001: GET / devuelve 302 a login y login responde HTTP 200.
- Los nuevos tests bloquean clasificación, lectura del master, exportación y consultas a ProductCatalogEntry durante aperturas sucesivas del container; comprueban que no se escriban estados. Incluyen el GET legacy sin reconstrucción, reparación explícita de PBP incompleto, identificadores distintos CODE/PON_SKU/CODE2 y dos consultas para 20 filas del sidebar.
- Las regresiones anteriores mantienen NEW/PBP tras aparecer como PON, excluyen Existing original y verifican los 30 valores históricos y el naranja de toda la fila.
- Fixture Git aislado: registro de commit, actualización en la misma carpeta y restore desde el commit comprobados con Git real; HEAD/objetos de .git, .env y continuity permanecen intactos.
- Integridad SHA256 del paquete y comprobaciones estáticas de scripts: OK.

Pendiente en la instalación del usuario: ejecución real de 01→02→04 en Windows/PowerShell, persistencia de su .git, backup PostgreSQL real, Docker, conversión Excel BIFF7 y HTTP 8001 de su equipo. Este entorno no tiene PowerShell, Docker, PostgreSQL ni ssconvert. La comprobación HTTP local y el fixture Git NO certifican la instalación del usuario. 04 incluye las comprobaciones del entorno que puede realizar; cualquier fallo devuelve salida no cero.
