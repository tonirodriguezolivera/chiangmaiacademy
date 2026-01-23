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
```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Estructura del Proyecto

```
app/
├── blueprints/      # Blueprints de Flask
├── services/        # Lógica de negocio
├── static/          # Archivos estáticos (CSS, JS, imágenes)
└── templates/       # Plantillas HTML
```


