# Update 1001.0832

Base: update 1001.0734, que ya incorpora la corrección del fixture Cervelo de 0930.1602.
Instalación activa única: C:\Docker-Projects\PON_Bikes_Automation.

New Product Import conserva NEW/PBP_TO_PON/EXISTING del container; las filas PBP_TO_PON conservan el snapshot de datos históricos y tienen relleno naranja A:AD. Existing original nunca entra. El master posterior no cambia la pertenencia. La disponibilidad del botón usa esa misma selección histórica. Product Check y Customer Report conservan su clasificación actual.

Se amplía ContainerProductStatus con dos campos y migración aditiva 0015: import_classification e import_history. El booleano was_new anterior no podía distinguir PBP_TO_PON de EXISTING. No se crea otra arquitectura ni se cambia el cálculo de dimensiones, pesos o formato Translogic.

Compatibilidad: was_new=True antiguo se conserva como NEW. Para was_new=False antiguo se consulta el último master conservado, del mismo customer (o global antiguo), subido antes de classified_at; se recupera PBP y sus datos de ese master. Si ese master original fue eliminado o reemplazado físicamente, la versión antigua no contiene evidencia suficiente para reconstruir PBP: se conserva Existing y no se inventa una clasificación histórica. Los snapshots nuevos no tienen esta limitación.

Git: Clear-PonDirectory excluye .git y Copy-PonTree excluye .git. 01 y 03 conservan el repositorio vivo en su ubicación; no lo respaldan ni lo restauran encima. 01 registra si existía y verifica accesibilidad antes de cambiar archivos. 03 no recrea un repositorio perdido. 04 comprueba existencia y ejecuta git status; los cambios pendientes y archivos sin seguimiento no son un error. No se ejecuta git init ni se crean commits. El repositorio queda con los cambios del update listos para revisar y versionar.

## Aplicación
Extraer el paquete fuera de la instalación activa. Abrir PowerShell en la carpeta extraída:

```powershell
.\01_PREPARE_INSTALL.ps1
.\02_APPLY_UPDATE.ps1
.\04_VALIDATE.ps1
```

No continuar al siguiente paso si el anterior falla. 01 respalda aplicación y PostgreSQL con el estándar vigente; preserva .env y continuity. 02 aplica la migración aditiva 0015. 03_ROLLBACK.ps1 mantiene el rollback estándar de aplicación y base de datos, preservando el Git actual. 05 continúa siendo el único launcher manual de Continuity Snapshot.

## Validación realizada
Django 5.1.15 / SQLite: 63 tests OK (58 existentes + 5 nuevos, 8.018 s); Django check OK; migraciones aplicables y migrate --check OK; makemigrations --check --dry-run sin diferencias.
Los nuevos tests cubren PBP tras aparecer como PON y eliminar la entrada PBP, igualdad de los 30 valores antes/después, naranja en toda la fila, NEW persistente y normal, Existing excluido tras desaparecer del master, recuperación legacy y aislamiento por container.

Pendiente en el equipo del usuario: ejecución real de scripts Windows/Git, Docker/PostgreSQL, conversión BIFF7 con ssconvert y respuesta de localhost:8001. Este entorno no dispone de Docker, PowerShell ni ssconvert. No se afirma que esos checks se hayan ejecutado aquí. 04 valida el suite completo, check, migrations, Git y respuesta HTTP en la instalación activa. El conversor Excel existente no fue modificado.
