# Escuela de Masajes Tailandeses - Landing Page

Aplicación Flask para la escuela de masajes tailandeses con sistema de registro y pagos.

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
Crear archivo `.env` con:
```
SECRET_KEY=tu-clave-secreta-aqui
DATABASE_URL=sqlite:///thai_massage_school.db
COURSE_PRICE=299.00
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

4. Ejecutar aplicación:

**Desarrollo local:**
```bash
# Opción 1: Ejecutar directamente
python app.py

# Opción 2: Usar Flask CLI
flask run
```

La aplicación estará disponible en `http://localhost:5000`

**Despliegue en cPanel:**
- El archivo `app.py` está en la raíz del proyecto
- La función `create_app()` es el punto de entrada
- En cPanel, configura el archivo de entrada como `app.py` y la aplicación como `app`
- Asegúrate de que el archivo `.env` esté configurado con tus variables de entorno

## Estructura del Proyecto

```
app/
├── blueprints/      # Blueprints de Flask
├── services/        # Lógica de negocio
├── static/          # Archivos estáticos (CSS, JS, imágenes)
└── templates/       # Plantillas HTML
```


