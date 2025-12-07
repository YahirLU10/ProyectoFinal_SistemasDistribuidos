import os
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

# --- Stopwords ---
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Descargar datos NLTK (solo la primera vez)
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

STOP_WORDS = set(stopwords.words("english")) | set(stopwords.words("spanish"))

import re

def quitar_stopwords(texto):
    # 1. Convertir a minúsculas
    texto = texto.lower()

    # 2. Dejar solo letras, números y espacios
    #    (quita signos como . , ? ! etc.)
    texto = re.sub(r"[^a-záéíóúüñ0-9\s]", " ", texto)

    # 3. Tokenizar
    tokens = texto.split()

    # 4. Quitar stopwords
    filtrado = [t for t in tokens if t not in STOP_WORDS]

    # 5. Regresar texto limpio
    return " ".join(filtrado)


# User-Agent obligatorio para Project Gutenberg
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

BASE_URL = "https://gutenberg.org"
CARPETA_LIBROS = "libros"


def preparar_carpeta():
    if not os.path.exists(CARPETA_LIBROS):
        os.makedirs(CARPETA_LIBROS)


def obtener_top_libros(cantidad):
    url = f"{BASE_URL}/browse/scores/top"
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    ids = []
    listas = soup.find_all("ol")

    for lista in listas:
        for link in lista.find_all("a"):
            if len(ids) >= cantidad:
                return ids
            try:
                book_id = int(link.get("href").split("/")[2])
                ids.append(book_id)
            except:
                continue

    return ids


def obtener_url_formato(book_id):
    formatos = [
        f"{BASE_URL}/files/{book_id}/{book_id}.txt",
        f"{BASE_URL}/files/{book_id}/{book_id}-0.txt",
        f"{BASE_URL}/files/{book_id}/{book_id}.pdf",
        f"{BASE_URL}/files/{book_id}/{book_id}.epub",
        f"{BASE_URL}/files/{book_id}/{book_id}-h/{book_id}-h.htm",
    ]

    for url in formatos:
        try:
            resp = requests.head(url, timeout=5, headers=HEADERS)
            if resp.status_code == 200:
                return url
        except:
            continue

    return None


def descargar_libro(book_id):
    url = obtener_url_formato(book_id)
    if not url:
        return False

    ext = url.split(".")[-1]
    nombre_archivo = os.path.join(CARPETA_LIBROS, f"libro_{book_id}.{ext}")

    if os.path.exists(nombre_archivo):
        return True

    try:
        r = requests.get(url, timeout=10, headers=HEADERS)

        if ext == "txt":
            texto = r.text
            texto_limpio = quitar_stopwords(texto)

            with open(nombre_archivo, "w", encoding="utf-8") as f:
                f.write(texto_limpio)

        else:
            with open(nombre_archivo, "wb") as f:
                f.write(r.content)

        return True

    except Exception as e:
        print(f"Error libro {book_id}: {e}")
        return False


def main():
    preparar_carpeta()

    try:
        cantidad = int(input("¿Cuántos libros quieres descargar? (ej: 100, 500, 1000): "))
    except:
        print("Número inválido.")
        return

    print(f"\nObteniendo {cantidad} libros desde Gutenberg...\n")
    ids = obtener_top_libros(cantidad)

    print(f"Total libros obtenidos: {len(ids)}\n")

    descargados = 0
    fallados = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(descargar_libro, book_id): book_id for book_id in ids}

        for future in tqdm(as_completed(futures), total=len(ids),
                           desc="Descargando libros",
                           bar_format="{l_bar}{bar} | {n_fmt}/{total_fmt} libros | {rate_fmt} | ETA {remaining}"):
            exito = future.result()
            if exito:
                descargados += 1
            else:
                fallados += 1

    tiempo_total = time.time() - start_time

    print("\n----- RESUMEN -----")
    print(f"Descargados: {descargados}")
    print(f"Fallados: {fallados}")
    print(f"Guardados en: {CARPETA_LIBROS}/")
    print(f"Tiempo total: {tiempo_total:.2f} segundos\n")


if __name__ == "__main__":
    main()
