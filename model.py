import baza
import sqlite3
import re

conn = sqlite3.connect('baza.db', timeout=10)
baza.ustvari_bazo_ce_ne_obstaja(conn)

def formatiraj_cas(sekunde):
    if sekunde is None:
        return None
    minute = int(sekunde // 60)
    sek = int(sekunde % 60)
    stotinke = int((sekunde * 100) % 100)
    return f"{minute}:{sek:02d}.{stotinke:02d}"

class Voznik:
    """
    Razred za voznika.
    """

    def __init__(self, ime_priimek, *, id=None):
        """
        Konstruktor voznika.
        """
        self.id = id
        self.ime_priimek = ime_priimek

    def __str__(self):
        """
        Znakovna predstavitev voznika.
        Vrne ime voznika.
        """
        return self.ime_priimek

    def poisci_zmage(self):
        """
        Vrne zmage voznika.
        """
        sql = """
            SELECT proga.ime_proge, proga.drzava, event.leto FROM rezultat
                JOIN event ON event.id = rezultat.event_id
                JOIN proga ON proga.id = event.id_proge
            WHERE rezultat.voznik_id = ? AND rezultat.mesto = 1
            ORDER BY event.leto DESC;
        """
        for proga, drzava, leto in conn.execute(sql, [self.id]):
            yield (proga, drzava, leto)
    
    def poisci_tocke(self):
        """
        Vrne število točk voznika po letih.
        """
        sql = """
            SELECT SUM(rezultat.tocke),  event.leto FROM rezultat
                JOIN event ON event.id = rezultat.event_id
            WHERE rezultat.voznik_id = ?
            GROUP BY event.leto
            ORDER BY event.leto DESC;
        """
        for st_tock, leto in conn.execute(sql, [self.id]):
            yield (st_tock, leto)

    def poisci_ekipe(self):
        """
        Vrne ekipo voznika po letih.
        """
        sql = """
            SELECT ekipa.ime, event.leto FROM rezultat
                JOIN event ON event.id = rezultat.event_id
                JOIN ekipa ON ekipa.id = rezultat.ekipa_id
            WHERE rezultat.voznik_id = ?
            GROUP BY event.leto, ekipa.id
            ORDER BY event.leto DESC;
        """
        for ekipa, leto in conn.execute(sql, [self.id]):
            yield (ekipa, leto)
    
    def poisci_skupno_st_tock(self):
        """
        Vrne skupno število točk voznika.
        """
        sql = """
            SELECT SUM(rezultat.tocke) FROM rezultat
                JOIN event ON event.id = rezultat.event_id
            WHERE rezultat.voznik_id = ?;
        """
        return conn.execute(sql, [self.id]).fetchone()[0]  
        
    def poisci_skupno_st_nastopov(self):
        """
        Vrne skupno število nastopov voznika.
        """
        sql = """
            SELECT COUNT(*) FROM rezultat
                JOIN event ON event.id = rezultat.event_id
            WHERE rezultat.voznik_id = ?;
        """
        return conn.execute(sql, [self.id]).fetchone()[0]
        
    def poisci_skupno_st_zmag(self):
        """
        Vrne skupno število zmag voznika.
        """
        sql = """
            SELECT COUNT(*) FROM rezultat
                JOIN event ON event.id = rezultat.event_id
            WHERE rezultat.voznik_id = ? AND rezultat.mesto = 1;
        """
        return conn.execute(sql, [self.id]).fetchone()[0] 
    
    def poisci_skupno_st_stopnick(self):
        """
        Vrne skupno število zmag voznika.
        """
        sql = """
            SELECT COUNT(*) FROM rezultat
                JOIN event ON event.id = rezultat.event_id
            WHERE rezultat.voznik_id = ?  AND rezultat.mesto in (1,2,3);
        """
        return conn.execute(sql, [self.id]).fetchone()[0]
    
    
    @staticmethod
    def poisci(niz):
        """
        Vrne vse voznike, ki v imenu vsebujejo dani niz za priimek.
        """
        if niz is None:
            return "Vnesi priimek!"
        sql = "SELECT id, ime_priimek FROM voznik WHERE ime_priimek LIKE ?"
        for id, ime_priimek in conn.execute(sql, [f'%{niz}%']):
            yield Voznik(ime_priimek=ime_priimek, id=id)

    def dodaj_v_bazo(self):
        """
        Doda voznika v bazo.
        """
        assert self.id is None
        with conn:
            podatki_voznika = {"ime_priimek" : self.ime_priimek}
            self.id = Voznik.dodaj_vrstico(**podatki_voznika)


class Ekipa:
    """
    Razred za ekipo.
    """
    
    def __init__(self, ime, id=None):
        """
        Konstruktor ekipe.
        """
        self.id = id
        self.ime = ime

    def __str__(self):
        """
        Znakovna predstavitev ekipe.
        Vrne ime ekipe.
        """
        return self.ime

    @staticmethod
    def poisci(niz):
        """
        Vrne vse ekipe, ki v imenu vsebujejo dani niz.
        """
        if niz is None:
            return "Vnesi ekipo!"
        sql = "SELECT id, ime FROM ekipa WHERE ime LIKE ?"
        for id, ime in conn.execute(sql, [f'%{niz}%']):
            yield Ekipa(id=id, ime=ime)

    def poisci_voznike(self):
        """
        Vrne voznike ekipe po letih skupaj s točkami, najhitrejšim časom in progo.
        """
        sql = """
            SELECT 
                voznik.ime_priimek,
                event.leto,
                SUM(rezultat.tocke) AS vsota,
                MIN(rezultat.cas) AS najhitrejsi_cas,
                proga.ime_proge
            FROM rezultat
                JOIN event ON event.id = rezultat.event_id
                JOIN voznik ON voznik.id = rezultat.voznik_id
                JOIN proga ON proga.id = event.id_proge
            WHERE rezultat.ekipa_id = ?
            GROUP BY event.leto, voznik.id
            ORDER BY event.leto DESC, vsota DESC;
        """
        for ime_priimek, leto, tocke, cas, proga in conn.execute(sql, [self.id]):
            yield (leto, ime_priimek, tocke, formatiraj_cas(float(cas)) if cas else "-", proga)

    def poisci_skupne_tocke_in_najboljsi_voznik(self):
        """
        Vrne skupno število točk ekipe in voznika, ki je prispeval največ točk.
        """
        # Skupne točke ekipe
        sql_skupno = """
            SELECT SUM(rezultat.tocke)
            FROM rezultat
            WHERE rezultat.ekipa_id = ?
        """
        skupno = conn.execute(sql_skupno, [self.id]).fetchone()[0] or 0

        # Voznik z največ točkami v tej ekipi
        sql_voznik = """
            SELECT voznik.ime_priimek, SUM(rezultat.tocke) AS vsota
            FROM rezultat
                JOIN voznik ON voznik.id = rezultat.voznik_id
            WHERE rezultat.ekipa_id = ?
            GROUP BY voznik.id
            ORDER BY vsota DESC
            LIMIT 1
        """
        row = conn.execute(sql_voznik, [self.id]).fetchone()
        najboljsi_voznik = row[0] if row else None

        return skupno, najboljsi_voznik

class Proga:
    """
    Razred za progo.
    """

    def __init__(self, ime, drzava, *, id=None):
        """
        Konstruktor proge.
        """
        self.id = id
        self.ime = ime
        self.drzava = drzava

    def __str__(self):
        """
        Znakovna predstavitev proge.
        Vrne ime in drzavo.
        """
        return self.ime + ", " + self.drzava
    
    
    def poisci_zmagovalce(self):
        """
        Vrne zmagovalce podane proge po letih.
        """
        sql = """
            SELECT voznik.ime_priimek, event.leto FROM rezultat
                JOIN event ON event.id = rezultat.event_id
                JOIN proga ON proga.id = event.id_proge
                JOIN voznik ON voznik.id = rezultat.voznik_id
            WHERE proga.id = ? AND rezultat.mesto = 1
            ORDER BY event.leto DESC;
        """
        for ime_priimek, leto in conn.execute(sql, [self.id]):
            yield (ime_priimek, leto)
    
    def poisci_top3(self):
        """
        Vrne prva tri mesta na tej progi po letih.
        """
        sql = """
            SELECT event.leto, rezultat.mesto, voznik.ime_priimek 
            FROM rezultat
                JOIN event ON event.id = rezultat.event_id
                JOIN proga ON proga.id = event.id_proge
                JOIN voznik ON voznik.id = rezultat.voznik_id
            WHERE proga.id = ? AND rezultat.mesto IN (1,2,3)
            ORDER BY event.leto DESC, rezultat.mesto ASC;
        """
        for leto, mesto, ime_priimek in conn.execute(sql, [self.id]):
            yield (leto, mesto, ime_priimek)

    @staticmethod
    def poisci(niz):
        """
        Vrne vse proge, ki v imenu vsebujejo dani niz.
        """
        if niz is None:
            return "Vnesi nekaj!"
        sql = "SELECT id, ime_proge, drzava FROM proga WHERE ime_proge LIKE ? OR drzava LIKE ?"
        for id, ime_proge, drzava in conn.execute(sql, [f'%{niz}%', f'%{niz}%']):
            yield Proga(ime=ime_proge, drzava=drzava, id=id)


class Event:
    """
    Razred za event.
    """

    def __init__(self, ime, leto, *, id=None):
        """
        Konstruktor eventa.
        """
        self.id = id
        self.ime = ime
        self.leto = leto

    def __str__(self):
        """
        Znakovna predstavitev eventa.
        Vrne ime in lokacijo.
        """
        return self.ime + ", " + str(self.leto)
    
    @staticmethod
    def poisci_leto():
        """
        Vrne seznam sezon/let.
        """
        sql = "SELECT DISTINCT(event.leto) FROM event ORDER BY event.leto DESC"
        for leto in conn.execute(sql):
            yield leto

    @staticmethod
    def poisci_evente_v_letu(leto):
        """
        Vrne vse evente in datume v danem letu.
        """
        sql = """
            SELECT DISTINCT(event.id), proga.ime_proge, leto FROM event 
                JOIN proga ON proga.id = event.id_proge
                WHERE event.leto LIKE ? 
            """
        for id, ime_proge, leto in conn.execute(sql, [leto]):
            yield Event(id=id, ime=ime_proge, leto=leto)
            
    def poisci_rezultate_eventa(self):
        """
        Vrne mesto, ime_priimek in število točk vseh voznikov na eventu.
        """
        sql = """
            SELECT rezultat.mesto, voznik.ime_priimek, rezultat.tocke FROM rezultat
                JOIN event ON event.id = rezultat.event_id
                JOIN voznik ON voznik.id = rezultat.voznik_id
            WHERE event_id = ? AND rezultat.mesto > 0
            ORDER BY rezultat.mesto ASC;
        """
        for mesto, ime_priimek, tocke in conn.execute(sql, [self.id]):
            yield (mesto, ime_priimek, tocke)

    def poisci_najhitrejsi_krog(self):
        """
        Vrne ime proge, voznika z najhitrejšim časom (v formatu m:ss.SS) in njegov čas za ta event.
        """
        sql = """
            SELECT proga.ime_proge, voznik.ime_priimek, MIN(rezultat.cas)
            FROM rezultat
                JOIN event ON event.id = rezultat.event_id
                JOIN proga ON proga.id = event.id_proge
                JOIN voznik ON voznik.id = rezultat.voznik_id
            WHERE event.id = ?
        """
        row = conn.execute(sql, [self.id]).fetchone()
        if row and row[2] is not None:
            proga, voznik, cas = row
            return proga, voznik, formatiraj_cas(float(cas))
        return row

