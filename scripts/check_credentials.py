#!/usr/bin/env python3
"""
Script para verificar el estado de las credenciales AWS y configuración del API.
"""
import os
import sys
from pathlib import Path

# Intentar cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv

    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"📁 Cargado .env desde: {env_file}")
except ImportError:
    print("⚠️  python-dotenv no instalado. Usando variables de entorno del sistema.")


def check_env_var(name: str, required: bool = False) -> str:
    """Verifica una variable de entorno y retorna su estado."""
    value = os.getenv(name)
    if value:
        # Ocultar valores sensibles
        if "key" in name.lower() or "secret" in name.lower() or "uri" in name.lower():
            display_value = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
        else:
            display_value = value
        status = f"✅ CONFIGURADO: {display_value}"
    else:
        status = "❌ NO CONFIGURADO" if required else "⚠️  NO CONFIGURADO (opcional)"

    return status


def main():
    print("🔍 VERIFICACIÓN DE CREDENCIALES AC9 SPORT API")
    print("=" * 50)

    # Variables requeridas
    print("\n📋 VARIABLES REQUERIDAS:")
    print(f"API_KEY: {check_env_var('API_KEY', required=True)}")
    print(f"MONGO_URI: {check_env_var('MONGO_URI', required=True)}")
    print(f"MONGO_DB: {check_env_var('MONGO_DB', required=True)}")

    # Variables AWS (opcionales)
    print("\n☁️  CREDENCIALES AWS S3 (Opcionales):")
    aws_key = check_env_var("AWS_ACCESS_KEY_ID")
    aws_secret = check_env_var("AWS_SECRET_ACCESS_KEY")
    s3_bucket = check_env_var("S3_BUCKET")
    s3_region = check_env_var("S3_REGION")

    print(f"AWS_ACCESS_KEY_ID: {aws_key}")
    print(f"AWS_SECRET_ACCESS_KEY: {aws_secret}")
    print(f"S3_BUCKET: {s3_bucket}")
    print(f"S3_REGION: {s3_region}")

    # Análisis de configuración S3
    aws_configured = all(
        [
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY"),
            os.getenv("S3_BUCKET"),
        ]
    )

    print("\n🎯 MODO DE OPERACIÓN:")
    if aws_configured:
        print("✅ MODO S3: Las imágenes se subirán a Amazon S3")
        print("   - URLs presigned: Reales de S3")
        print("   - Almacenamiento: En la nube (S3)")
    else:
        print("📁 MODO LOCAL: Las imágenes se subirán localmente")
        print("   - URLs presigned: Endpoints locales del API")
        print("   - Almacenamiento: En servidor local")

    # Verificar archivo .env
    print("\n📄 ARCHIVO .ENV:")
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"✅ Encontrado: {env_file}")
    else:
        print(f"❌ No encontrado: {env_file}")
        print("   💡 Crea el archivo .env con tus credenciales")

    # Verificar que boto3 esté disponible si AWS está configurado
    if aws_configured:
        try:
            import boto3

            print("\n📦 DEPENDENCIAS:")
            print("✅ boto3: Instalado")

            # Intentar crear cliente
            try:
                boto3.client("s3", region_name=os.getenv("S3_REGION", "us-east-1"))
                print("✅ Cliente S3: Creado exitosamente")
            except Exception as e:
                print(f"❌ Error creando cliente S3: {e}")
        except ImportError:
            print("\n📦 DEPENDENCIAS:")
            print("❌ boto3: NO instalado")
            print("   💡 Instala con: pip install boto3")

    print("\n" + "=" * 50)
    print("✨ Verificación completa")


if __name__ == "__main__":
    main()
