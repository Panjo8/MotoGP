import csv
import sqlite3

PARAM_FMT = ":{}" # za SQLite



class Tabela:
    """
    Razred, ki predstavlja tabelo v bazi.

    Polja razreda:
    - ime: ime tabele
    - podatki: ime datoteke s podatki ali None
    """
    ime = None
    podatki = None

    def __init__(self, conn):
        """
        Konstruktor razreda.
        """
        self.conn = conn

    def ustvari(self):
        """
        Metoda za ustvarjanje tabele.
        Podrazredi morajo povoziti to metodo.
        """
        raise NotImplementedError

    def izbrisi(self):
        """
        Metoda za brisanje tabele.
        """
        self.conn.execute(f"DROP TABLE IF EXISTS {self.ime};")


    def izprazni(self):
        """
        Metoda za praznjenje tabele.
        """
        self.conn.execute(f"DELETE FROM {self.ime};")

    def dodajanje(self, stolpci=None):
        """
        Metoda za gradnjo poizvedbe.

        Argumenti:
        - stolpci: seznam stolpcev
        """
        return f"""
            INSERT INTO {self.ime} ({", ".join(stolpci)})
            VALUES ({", ".join(PARAM_FMT.format(s) for s in stolpci)});
        """

    def dodaj_vrstico(self, **podatki):
        """
        Metoda za dodajanje vrstice.

        Argumenti:
        - poimenovani parametri: vrednosti v ustreznih stolpcih
        """
        podatki = {kljuc: vrednost for kljuc, vrednost in podatki.items()
                   if vrednost is not None}
        poizvedba = self.dodajanje(podatki.keys())
        cur = self.conn.execute(poizvedba, podatki)
        return cur.lastrowid
    

class Rezultat(Tabela):
    """
    Tabela za rezultate.
    """
    ime = "rezultat"
    podatki = "motogp_rezultati.csv"

    def ustvari(self):
        """
        Ustvari tabelo rezultat.
        """
        self.conn.execute("""
            CREATE TABLE rezultat (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id      INTEGER REFERENCES event(id),
                voznik_id     INTEGER REFERENCES voznik(id),
                ekipa_id      INTEGER REFERENCES ekipa(id),
                mesto         INTEGER,
                tocke         INTEGER,
                cas           INTEGER
            );
        """)
    
    def dodaj_vrstico(self, **podatki):
        rez = self.conn.execute("SELECT id FROM rezultat WHERE event_id= :event_id AND voznik_id = :voznik_id", podatki).fetchone()
        if rez is None:
            return super().dodaj_vrstico(**podatki)

class Voznik(Tabela):
    """
    Tabela za voznike.
    """
    ime = "voznik"
    podatki = "motogp_rezultati.csv"

    def ustvari(self):
        """
        Ustvari tabelo voznik.
        """
        self.conn.execute("""
            CREATE TABLE voznik (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ime_priimek   TEXT
            );
        """)

    def dodaj_vrstico(self, **podatki):
        assert "ime_priimek" in podatki
        rez = self.conn.execute("SELECT id FROM voznik WHERE ime_priimek= :ime_priimek", podatki).fetchone()
        if rez is None:
            return super().dodaj_vrstico(**podatki)
        else:
            id, = rez
            return id

class Ekipa(Tabela):
    """
    Tabela za ekipe.
    """
    ime = "ekipa"
    podatki = "motogp_rezultati.csv"

    def ustvari(self):
        """
        Ustvari tabelo ekipa.
        """
        self.conn.execute("""
            CREATE TABLE ekipa (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ime       TEXT
            );
        """)

    def dodaj_vrstico(self, **podatki):
        assert "ime" in podatki
        rez = self.conn.execute("SELECT id FROM ekipa WHERE ime= :ime", podatki).fetchone()
        if rez is None:
            return super().dodaj_vrstico(**podatki)
        else:
            id, = rez
            return id

class Event(Tabela):
    """
    Tabela za event-e.
    """
    ime = "event"
    podatki = "motogp_rezultati.csv"

    def ustvari(self):
        """
        Ustvari tabelo event.
        """
        self.conn.execute("""
            CREATE TABLE event (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                leto            INTEGER,
                id_proge        INTEGER REFERENCES proga(id),
                najhitrejsi_cas INTEGER  
            );
        """)

    def dodaj_vrstico(self, **podatki):
        #assert "ime" in podatki
        rez = self.conn.execute("SELECT id FROM event WHERE id_proge= :id_proge AND leto= :leto AND najhitrejsi_cas= :najhitrejsi_cas", podatki).fetchone()
        if rez is None:
            return super().dodaj_vrstico(**podatki)
        else:
            id, = rez
            return id

class Proga(Tabela):
    """
    Tabela za proge.
    """
    ime = "proga"
    podatki = "motogp_rezultati.csv"

    def ustvari(self):
        """
        Ustvari tabelo proga.
        """
        self.conn.execute("""
            CREATE TABLE proga (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                drzava    TEXT
            );
        """)
    
    def dodaj_vrstico(self, **podatki):
        assert "drzava" in podatki
        rez = self.conn.execute("SELECT id FROM proga WHERE drzava= :drzava", podatki).fetchone()
        if rez is None:
            return super().dodaj_vrstico(**podatki)
        else:
            id, = rez
            return id


def ustvari_tabele(tabele):
    """
    Ustvari podane tabele.
    """
    for t in tabele:
        t.ustvari()


def izbrisi_tabele(tabele):
    """
    Izbriši podane tabele.
    """
    for t in tabele:
        t.izbrisi()


def izprazni_tabele(tabele):
    """
    Izprazni podane tabele.
    """
    for t in tabele:
        t.izprazni()


def ustvari_bazo(conn):
    """
    Izvede ustvarjanje baze.
    """
    tabele = pripravi_tabele(conn)
    izbrisi_tabele(tabele)
    ustvari_tabele(tabele)
    uvozi_podatke(tabele)


def pripravi_tabele(conn):
    """
    Pripravi objekte za tabele.
    """
    rezultat = Rezultat(conn)
    voznik = Voznik(conn)
    ekipa = Ekipa(conn)
    event = Event(conn)
    proga = Proga(conn)
    return [rezultat, voznik, ekipa, event, proga]


def ustvari_bazo_ce_ne_obstaja(conn):
    """
    Ustvari bazo, če ta še ne obstaja.
    """
    with conn:
        cur = conn.execute("SELECT COUNT(*) FROM sqlite_master")
        if cur.fetchone() == (0, ):
            ustvari_bazo(conn)
        
def uvozi_podatke(tabele, datoteka="motogp_rezultati.csv"):
    """uvozi vse podatke iz datoteke"""

    rezultat_tabela = tabele[0]
    voznik_tabela = tabele[1]
    ekipa_tabela = tabele[2]
    event_tabela = tabele[3]
    proga_tabela = tabele[4]

    with open(datoteka, "r", encoding='utf-8') as dat:
        leto = 0
        drzava = ""
        ime_priimek = ""
        for vrstica in dat:
            podatki = vrstica.strip().split(",")

            if podatki[0] == "@":
                drzava = podatki[2]
                leto = podatki[3]
                podatki_proga = {"drzava" : drzava}

            else:
                if podatki[0] == '1': #ker prva vrstica ima najhitrejsi cas
                    mesto, tocke, ime_priimek, ekipa, cas = podatki

                    proga_id = proga_tabela.dodaj_vrstico(**podatki_proga)
                    podatki_eventa = {"leto" : leto, "id_proge" : proga_id, "najhitrejsi_cas" : cas}

                else:
                    mesto, tocke, ime_priimek, ekipa, cas = podatki
                  

                podatki_voznik = {"ime_priimek" : ime_priimek}                        
                podatki_ekipa = {"ime" : ekipa}

                ekipa_id = ekipa_tabela.dodaj_vrstico(**podatki_ekipa)
                event_id = event_tabela.dodaj_vrstico(**podatki_eventa)
                voznik_id = voznik_tabela.dodaj_vrstico(**podatki_voznik)

                podatki_rezultat = {"event_id" : event_id, "voznik_id" : voznik_id, "ekipa_id" : ekipa_id, "mesto" : mesto, "tocke" : tocke, "cas" : cas}
                rezultat_tabela.dodaj_vrstico(**podatki_rezultat)

if __name__ == "__main__":        
    import os
    os.remove("baza.db")
conn = sqlite3.connect("baza.db", timeout=10)
ustvari_bazo_ce_ne_obstaja(conn)