FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar TODO el código fuente desde src/
COPY src/ .

# Crear directorio de resultados
RUN mkdir -p /app/results

# Ejecutar
CMD ["python", "main.py"]
