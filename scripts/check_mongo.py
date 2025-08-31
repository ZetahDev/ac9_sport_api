#!/usr/bin/env python3
"""
check_mongo.py

Uso:
  - Probar conexión y listar colecciones:
      python check_mongo.py --uri "<MONGO_URI>"

  - Buscar un usuario por email:
      python check_mongo.py --uri "<MONGO_URI>" --email "tu@correo.com"

  - Alternativamente puedes exportar MONGO_URI en el entorno:
      $env:MONGO_URI = "<MONGO_URI>"
      python check_mongo.py --email "tu@correo.com"

Salida:
  - Código 0: conexión OK (y búsqueda realizada si se indicó email).
  - Código 2: error de conexión.
"""

import argparse
import sys
import json
from pymongo import MongoClient, errors

COMMON_COLLECTIONS = ["users", "user", "Users", "User"]

def parse_args():
    p = argparse.ArgumentParser(description="MongoDB connection & user check helper")
    p.add_argument("--uri", help="MongoDB URI (mongodb://... or mongodb+srv://...)")
    p.add_argument("--email", help="Email to search for (optional)")
    p.add_argument("--db", help="Database name to use (optional). If omitted, taken from URI or server default.")
    p.add_argument("--collection", help="Collection to search explicitly (optional). If omitted will try common names.")
    p.add_argument("--timeout", type=int, default=5000, help="Server selection timeout ms (default 5000)")
    return p.parse_args()

def get_db_from_uri(uri):
    # Try to extract database from URI if present (mongodb://host/db?...)
    # If not present return None and let MongoClient.get_database() pick default
    try:
        # Simple parse
        if "/" in uri:
            parts = uri.split("/")
            if len(parts) >= 4:
                db_candidate = parts[3].split("?")[0]
                if db_candidate:
                    return db_candidate
    except Exception:
        pass
    return None

def main():
    args = parse_args()
    uri = args.uri or os_environ_uri()
    if not uri:
        print("ERROR: Debes proporcionar --uri o tener la variable de entorno MONGO_URI.", file=sys.stderr)
        sys.exit(2)

    print("Usando URI:", uri[:80] + ("..." if len(uri) > 80 else ""))

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=args.timeout)
        # quick ping
        ping = client.admin.command("ping")
        print("Ping OK:", ping)
        # buildInfo to exercise connection
        try:
            bi = client.admin.command({"buildInfo": 1})
            print("buildInfo:", {"version": bi.get("version"), "gitVersion": bi.get("gitVersion")})
        except Exception as e:
            print("buildInfo no disponible:", str(e))

    except errors.ServerSelectionTimeoutError as e:
        print("ERROR: No se pudo conectar al servidor MongoDB (ServerSelectionTimeoutError).", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(2)
    except errors.ConfigurationError as e:
        print("ERROR: ConfigurationError:", str(e), file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print("ERROR: Excepción al intentar conectar:", str(e), file=sys.stderr)
        sys.exit(2)

    # determine db
    db_name = args.db or get_db_from_uri(uri)
    if not db_name:
        # fallback to 'ac9_sport' if not present (repo uses that)
        db_name = "ac9_sport"
        print("DB no especificada en la URI; usando DB por defecto:", db_name)
    db = client.get_database(db_name)
    try:
        collections = db.list_collection_names()
    except Exception as e:
        print("ERROR: No se pudieron listar colecciones de la DB:", str(e), file=sys.stderr)
        collections = []
    print("Colecciones en DB (ejemplo):", collections[:50])

    if args.email:
        email = args.email
        print(f"Buscando email: {email}")
        targets = [args.collection] if args.collection else COMMON_COLLECTIONS + collections
        found = []
        for coll_name in [c for c in targets if c]:
            try:
                coll = db.get_collection(coll_name)
                doc = coll.find_one({"email": email})
                if doc:
                    found.append({"collection": coll_name, "doc": doc})
                    # no break; informar todas las coincidencias
            except Exception as e:
                # ignorar colecciones que no existen o errores de permisos
                continue
        if not found:
            print("No se encontró ningún documento con ese email en las colecciones probadas.")
            print("Colecciones probadas:", targets)
            sys.exit(0)
        else:
            print("Encontrado(s):")
            for f in found:
                # imprimir campos importantes sin exponer contraseñas
                out = f["doc"].copy()
                out.pop("password_hash", None)
                print("- colección:", f["collection"])
                print(json.dumps(out, default=str, indent=2))
            sys.exit(0)

    # if no email requested, exit success
    sys.exit(0)

def os_environ_uri():
    import os
    return os.environ.get("MONGO_URI")

if __name__ == "__main__":
    main()