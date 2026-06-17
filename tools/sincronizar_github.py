import os
import sys
import subprocess
from datetime import datetime


# ==================================================
# 0. DIRECTORIOS
# ==================================================

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_SUPERIOR = os.path.dirname(DIRECTORIO_ACTUAL)


# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

ARCHIVOS_A_SUBIR = [
    "index.html",
    "web/data/empresas_finales.json"
]


# ==================================================
# 2. FUNCIONES GIT
# ==================================================

def ejecutar_comando_git(comando):
    print("Ejecutando:", " ".join(comando))

    resultado = subprocess.run(
        comando,
        cwd=DIRECTORIO_SUPERIOR,
        capture_output=True,
        text=True
    )

    salida = resultado.stdout + resultado.stderr

    if salida.strip():
        print(salida.strip())

    return resultado.returncode, salida


def comprobar_rama_actual():
    codigo, salida = ejecutar_comando_git(
        ["git", "branch", "--show-current"]
    )

    if codigo != 0:
        print("❌ No se pudo comprobar la rama actual.")
        return None

    rama = salida.strip()

    print(f"🌿 Rama actual: {rama}")

    return rama


def comprobar_estado_git():
    codigo, salida = ejecutar_comando_git(
        ["git", "status", "--short"]
    )

    if codigo != 0:
        print("❌ No se pudo comprobar el estado de Git.")
        return False

    if salida.strip() == "":
        print("ℹ️ No hay cambios pendientes.")
    else:
        print("📌 Cambios detectados:")
        print(salida)

    return True


def hacer_add():
    for archivo in ARCHIVOS_A_SUBIR:
        ruta_absoluta = os.path.join(DIRECTORIO_SUPERIOR, archivo)

        if not os.path.exists(ruta_absoluta):
            print(f"⚠️ El archivo no existe y no se añadirá: {archivo}")
            continue

        codigo, salida = ejecutar_comando_git(
            ["git", "add", archivo]
        )

        if codigo != 0:
            print(f"❌ Error haciendo git add de {archivo}")
            return False

    return True


def hacer_commit():
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    mensaje_commit = f"Actualizar web IAProspector - {fecha}"

    codigo, salida = ejecutar_comando_git(
        ["git", "commit", "-m", mensaje_commit]
    )

    if codigo != 0:
        salida_minuscula = salida.lower()

        if "nothing to commit" in salida_minuscula or "no changes added" in salida_minuscula:
            print("ℹ️ No hay cambios nuevos que commitear.")
            return True

        print("❌ Error haciendo commit.")
        return False

    return True


def hacer_push():
    codigo, salida = ejecutar_comando_git(
        ["git", "push"]
    )

    if codigo != 0:
        salida_minuscula = salida.lower()

        if "no upstream branch" in salida_minuscula:
            rama = comprobar_rama_actual()

            if rama:
                print("\n⚠️ La rama actual no tiene upstream.")
                print("Puedes solucionarlo con:")
                print(f"git push -u origin {rama}")

            return False

        print("❌ Error haciendo push.")
        return False

    return True


# ==================================================
# 3. PROCESO PRINCIPAL
# ==================================================

def sincronizar_con_github():
    print("\n==================================================")
    print("🚀 SINCRONIZAR WEB CON GITHUB")
    print("==================================================")

    comprobar_rama_actual()

    if not comprobar_estado_git():
        return

    if not hacer_add():
        return

    if not hacer_commit():
        return

    if not hacer_push():
        return

    print("\n==================================================")
    print("✅ SINCRONIZACIÓN COMPLETADA")
    print("==================================================")


if __name__ == "__main__":
    print("sincronizando")
    sincronizar_con_github()