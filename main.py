from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import boto3
from botocore.exceptions import ClientError
import os

# 1. Inicializamos la aplicación FastAPI
app = FastAPI(title="API de Imágenes S3")

# 2. Configuramos el cliente de S3 usando boto3
# Nota: boto3 usará automáticamente las credenciales que configuraste 
# en tu terminal con 'aws configure'
s3_client = boto3.client('s3', region_name='us-east-2')

# Nombre de tu bucket (¡Cámbialo por el tuyo!)
BUCKET_NAME = "final-sistop-punto2"

# 3. Endpoint POST para subir la imagen
@app.post("/upload/")
async def upload_image(
    # Recibimos el nombre del usuario como texto
    usuario: str = Form(...), 
    # Recibimos el archivo de la imagen
    imagen: UploadFile = File(...)
):
    
    # a. Validamos la extensión del archivo
    extensiones_permitidas = ["image/jpeg", "image/jpg", "image/png"]
    if imagen.content_type not in extensiones_permitidas:
        # Si no es JPG o PNG, devolvemos un error 415 (Unsupported Media Type)
        raise HTTPException(status_code=415, detail="Formato de archivo no permitido. Solo JPG y PNG.")

    # b. Construimos la ruta dentro de S3 (CarpetaUsuario/NombreImagen)
    # Ejemplo: maria/mifoto.png
    ruta_s3 = f"{usuario}/{imagen.filename}"

    try:
        # c. Subimos el archivo a S3
        s3_client.upload_fileobj(
            imagen.file, 
            BUCKET_NAME, 
            ruta_s3
        )
        return {"mensaje": "Imagen subida exitosamente", "ruta_s3": ruta_s3}
    
    except Exception as e:
        # Si algo falla con AWS, devolvemos un error 500
        raise HTTPException(status_code=500, detail=f"Error al subir a S3: {str(e)}")
    
# d. Implementar un endpoint GET que reciba el nombre de usuario y la imagen
@app.get("/download/")
async def get_image(usuario: str, nombre_imagen: str):
    
    # Construimos la ruta exacta que queremos buscar en S3
    ruta_s3 = f"{usuario}/{nombre_imagen}"
    
    try:
        # e.1 Verificar la existencia y obtener metadatos del objeto en S3
        metadata = s3_client.head_object(Bucket=BUCKET_NAME, Key=ruta_s3)
        
        # e.4 Obtener la fecha de almacenamiento desde los metadatos
        fecha_almacenamiento = metadata['LastModified']
        
        # e.3 Generar una URL prefirmada válida por 1 hora (3600 segundos)
        url_prefirmada = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': ruta_s3},
            ExpiresIn=3600
        )
        
        # Retornamos la información requerida
        return {
            "mensaje": "Imagen encontrada exitosamente",
            "url_acceso": url_prefirmada,
            "fecha_almacenamiento": fecha_almacenamiento
        }
        
    except ClientError as e:
        # e.2 En caso de no existir, retornar un mensaje claro indicando el problema
        if e.response['Error']['Code'] == '404':
            raise HTTPException(
                status_code=404, 
                detail="Error: El usuario o la imagen solicitada no existen en el bucket S3."
            )
        else:
            # Si ocurre otro tipo de error de conexión, también lo reportamos
            raise HTTPException(status_code=500, detail="Error interno al conectar con AWS S3.")