# Sistema de Gestión de Historiales Médicos - Backend

Una API REST integral basada en Flask para gestionar registros médicos, información de pacientes, citas, diagnósticos, tratamientos y medicamentos.

## 📋 Tabla de Contenidos

- [Características](#características)
- [Esquema de Base de Datos](#esquema-de-base-de-datos)
- [Requisitos Previos](#requisitos-previos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecutar la Aplicación](#ejecutar-la-aplicación)
- [Módulos de la API](#módulos-de-la-api)
- [Estructura de la Base de Datos](#estructura-de-la-base-de-datos)
- [Variables de Entorno](#variables-de-entorno)
- [Registro de Logs](#registro-de-logs)
- [Solución de Problemas](#solución-de-problemas)

## ✨ Características

- **Gestión de Pacientes**: Registro completo y manejo de perfiles de pacientes
- **Registros Médicos**: Seguimiento digital del historial médico
- **Sistema de Citas**: Programar y gestionar citas médicas
- **Gestión de Diagnósticos**: Crear y hacer seguimiento de diagnósticos de pacientes
- **Planes de Tratamiento**: Planificación y seguimiento integral de tratamientos
- **Gestión de Medicamentos**: Seguimiento de medicamentos recetados y dosis
- **Autenticación de Usuarios**: Sistema de autenticación basado en JWT
- **Acceso Basado en Roles**: Diferentes niveles de acceso para pacientes, doctores y administradores
- **Soporte CORS**: Intercambio de recursos de origen cruzado para integración frontend
- **Caché**: Sistema de caché simple para mejorar el rendimiento
- **Registro Integral**: Seguimiento de debug y errores

## 🗄️ Esquema de Base de Datos

El sistema utiliza MySQL con las siguientes entidades principales:

- **Paciente** (Pacientes)
- **Médico** (Doctores)
- **Cita** (Citas)
- **Historial_Médico** (Historial Médico)
- **Diagnóstico** (Diagnósticos)
- **Tratamiento** (Tratamientos)
- **Medicamento** (Medicamentos)
- **Usuario** (Usuarios)
- **Rol** (Roles)

## 🔧 Requisitos Previos

- Python 3.8+
- MySQL 8.0+
- pip (instalador de paquetes de Python)

## 🚀 Instalación

### 1. Clonar el Repositorio

```bash
git clone <https://github.com/LemonMantis5571/Historial-Medico-Back>
cd medical-history-backend
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Base de Datos

1. Crear una base de datos MySQL llamada `historial_medico`
2. Importar el esquema de la base de datos:

```bash
mysql -u root -p historial_medico < "Base de Datos Final.sql"
```

## ⚙️ Configuración

### 1. Variables de Entorno

Crear un archivo `.env` en el directorio raíz:

```env
# Configuración de Base de Datos
DB_HOST=localhost
DB_PASSWORD=tu_contraseña_mysql

# Configuración JWT
SECRET_KEY=tu-clave-secreta-jwt-super-segura-aqui

# Opcional: Puerto de Base de Datos (por defecto: 3308)
DB_PORT=3308
```

### 2. Configuración de Base de Datos

La aplicación se conecta a MySQL con estas configuraciones por defecto:
- **Host**: Desde la variable de entorno `DB_HOST`
- **Puerto**: 3308
- **Base de Datos**: `historial_medico`
- **Usuario**: `root`
- **Contraseña**: Desde la variable de entorno `DB_PASSWORD`

## 🏃‍♂️ Ejecutar la Aplicación

### Modo Desarrollo

```bash
python app.py
```

El servidor iniciará en `http://127.0.0.1:5000` por defecto.

### Consideraciones para Producción

Para despliegue en producción:

1. Establecer `app.debug = False`
2. Usar un servidor WSGI de producción como Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📚 Módulos de la API

El backend está organizado en los siguientes módulos:

- **`auth.py`** - Autenticación y autorización
- **`usuarios.py`** - Gestión de usuarios
- **`paciente.py`** - Gestión de pacientes
- **`medicos.py`** - Gestión de doctores
- **`citas.py`** - Programación de citas
- **`historialMedico.py`** - Gestión de historial médico
- **`diagnosticos.py`** - Gestión de diagnósticos
- **`tratamientos.py`** - Planificación de tratamientos
- **`medicamentos.py`** - Gestión de medicamentos
- **`roles.py`** - Control de acceso basado en roles

## 🏗️ Estructura de la Base de Datos

### Tablas Principales

#### Paciente (Pacientes)
- `ID_Paciente` (Clave Primaria)
- `Nombre` - Nombre del paciente
- `Fecha_Nacimiento` - Fecha de nacimiento
- `Género` - Género
- `Teléfono` - Número de teléfono

#### Médico (Doctores)
- `ID_Médico` (Clave Primaria)
- `Nombre` - Nombre del doctor
- `Especialidad` - Especialidad médica
- `Teléfono` - Número de teléfono

#### Cita (Citas)
- `ID_Cita` (Clave Primaria)
- `Fecha` - Fecha de la cita
- `Hora` - Hora de la cita
- `Estado` - Estado de la cita
- `ID_Paciente` - Clave foránea al Paciente
- `ID_Médico` - Clave foránea al Doctor

#### Diagnóstico (Diagnósticos)
- `ID_Diagnóstico` (Clave Primaria)
- `Descripción` - Descripción del diagnóstico
- `Fecha` - Fecha del diagnóstico
- `ID_Historial` - Clave foránea al Historial Médico
- `ID_Cita` - Clave foránea a la Cita

## 🔐 Variables de Entorno

| Variable | Descripción | Requerida | Por Defecto |
|----------|-------------|-----------|-------------|
| `DB_HOST` | Dirección del host MySQL | Sí | - |
| `DB_PASSWORD` | Contraseña de MySQL | Sí | - |
| `SECRET_KEY` | Clave secreta JWT | Sí | - |
| `DB_PORT` | Puerto de MySQL | No | 3308 |

### Ejemplo de archivo .env:

```env
DB_HOST=localhost
DB_PASSWORD=miContraseñaSegura123
SECRET_KEY=tu-clave-secreta-de-256-bits-aqui
```

## 📝 Registro de Logs

La aplicación incluye registro integral de logs:

- **Salida de Consola**: Información de debug en tiempo real
- **Registro en Archivo**: Logs persistentes guardados en `app.log`
- **Niveles de Log**: DEBUG, INFO, WARNING, ERROR

Formato de log: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

## 🔧 Solución de Problemas

### Problemas Comunes

#### Error de Conexión a Base de Datos
```
mysql.connector.errors.DatabaseError: 2003 (HY000): Can't connect to MySQL server
```
**Solución**: Verificar que MySQL esté ejecutándose y que las credenciales en `.env` sean correctas.

#### Puerto Ya en Uso
```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```
**Solución**: Cambiar el puerto en `app.run()` o terminar el proceso que usa el puerto.

#### Variables de Entorno Faltantes
```
KeyError: 'DB_HOST'
```
**Solución**: Asegurar que el archivo `.env` existe con todas las variables requeridas.

#### Errores de Token JWT
```
jwt.exceptions.InvalidSignatureError
```
**Solución**: Verificar que `SECRET_KEY` esté configurada y sea consistente.

### Consejos de Desarrollo

1. **Habilitar Modo Debug**: Establecer `app.debug = True` para mensajes de error detallados
2. **Revisar Logs**: Monitorear `app.log` para información detallada de errores
3. **Esquema de Base de Datos**: Asegurar que el esquema de la base de datos coincida con el archivo SQL
4. **Problemas CORS**: Verificar que CORS esté configurado correctamente para tu dominio frontend

## 📞 Soporte

Para problemas y preguntas:

1. Revisar los logs en `app.log`
2. Verificar conexiones de base de datos
3. Asegurar que todas las variables de entorno están configuradas
4. Verificar el estado del servicio MySQL

## 🔄 Endpoints de la API

Cada módulo proporciona endpoints RESTful:

- **Autenticación**: `/auth/*`
- **Pacientes**: `/pacientes/*`
- **Doctores**: `/medicos/*`
- **Citas**: `/citas/*`
- **Diagnósticos**: `/diagnosticos/*`
- **Tratamientos**: `/tratamientos/*`
- **Medicamentos**: `/medicamentos/*`

Para documentación detallada de la API, consultar los archivos individuales de cada módulo.

---
