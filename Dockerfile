# ---------------------------------------------------------------------------
# Bazna slika - koristimo "slim" verziju Pythona radi manje veličine image-a
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# ---------------------------------------------------------------------------
# Radni direktorijum unutar kontejnera
# ---------------------------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------------------------
# Prvo kopiramo samo requirements.txt (ne ceo kod) i instaliramo zavisnosti.
# Ovo iskorišćava Docker layer caching - ako se kod promeni ali ne i
# requirements.txt, Docker neće ponovo instalirati pakete pri sledećem build-u,
# što ubrzava build proces.
# ---------------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Sada kopiramo ostatak koda aplikacije
# ---------------------------------------------------------------------------
COPY . .

# ---------------------------------------------------------------------------
# Cloud Run očekuje da kontejner sluša na portu definisanom preko
# PORT environment promenljive (podrazumevano 8080). Ne hardkodujemo
# port u kodu - koristimo ga dinamički u CMD komandi ispod.
# ---------------------------------------------------------------------------
ENV PORT=8080
EXPOSE 8080

# ---------------------------------------------------------------------------
# Pokretanje aplikacije. Koristimo "sh -c" da bi se $PORT promenljiva
# ispravno interpretirala u runtime-u (Cloud Run je postavlja automatski).
# ---------------------------------------------------------------------------
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
