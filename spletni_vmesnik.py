import bottle
from bottle import request, response, redirect
from model import Voznik, Ekipa, Proga, Event
import sqlite3

SECRET = "ZAMENJAJ_ME_S_TAJNOSTJO"  # TODO: nastavi močan skrivni ključ
DB_PATH = "baza.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@bottle.get('/')
def naslovna_stran():
    return bottle.template('naslovna_stran.html', napaka=None)


@bottle.get('/static/<pot:path>')
def vrni_staticno(pot):
    return bottle.static_file(pot, root="static")


#vozniki
@bottle.get('/voznik/')
def isci_voznika():
    iskalni_niz = bottle.request.query.getunicode('iskalni_niz')
    vozniki = list(Voznik.poisci(""))
    if iskalni_niz:
        filtrirani_vozniki = [voznik for voznik in vozniki if iskalni_niz.lower() in voznik.ime_priimek.lower()]
        vozniki = filtrirani_vozniki or ["Tega voznika ni v bazi!"]
    return bottle.template('voznik.html', iskalni_niz=iskalni_niz, vozniki=vozniki)


@bottle.get('/voznik/<priimek>/')
def tocke_in_zmage_voznika(priimek):
    vozniki = Voznik.poisci(priimek)
    tocke, zmage, profil, ekipe = [], [], [], []
    for voznik in vozniki:
        tocke.extend(voznik.poisci_tocke())
        zmage.extend(voznik.poisci_zmage())
        profil.append((voznik.poisci_skupno_st_nastopov(),
                       voznik.poisci_skupno_st_zmag(),
                       voznik.poisci_skupno_st_stopnick(),
                       voznik.poisci_skupno_st_tock()))
        ekipe.extend(voznik.poisci_ekipe())
    return bottle.template('voznik_statistika.html',
                           tocke=tocke, voznik=voznik, zmage=zmage, profil=profil, ekipe=ekipe)


#proge
@bottle.get('/proga/')
def isci_progo():
    iskalni_niz = bottle.request.query.getunicode('iskalni_niz')
    proge = list(Proga.poisci(""))
    if iskalni_niz:
        filtrirane_proge = [proga for proga in proge if iskalni_niz.lower() in proga.ime.lower()]
        proge = filtrirane_proge or ["Te proge ni v bazi!"]
    return bottle.template('proga.html', iskalni_niz=iskalni_niz, proge=proge)


@bottle.get('/proga/<ime>/')
def top3_proge(ime):
    proge = list(Proga.poisci(ime))
    if not proge:
        return "Ta proga ne obstaja!"
    proga = proge[0]
    top3 = list(proga.poisci_top3())
    return bottle.template('proga_statistika.html', top3=top3, proga=proga)


#eventi
@bottle.get('/event/')
def seznam_eventov():
    eventi = list(Event.poisci_evente_v_letu("%"))
    return bottle.template('eventi.html', eventi=eventi)


@bottle.get('/event/')
def seznam_eventov_dropdown():
    eventi = list(Event.poisci_evente_v_letu("%"))
    return bottle.template('event_dropdown.html', eventi=eventi)


@bottle.get('/event/<id:int>/')
def event_rezultat(id):
    event_obj = next((e for e in Event.poisci_evente_v_letu("%") if e.id == id), None)
    if not event_obj:
        return "Event ne obstaja!"
    proga, voznik, cas = event_obj.poisci_najhitrejsi_krog() or (None, None, None)
    vse_proge = list(Proga.poisci(""))
    return bottle.template('event.html', event=event_obj, proga=proga, voznik=voznik, cas=cas, proge=vse_proge)


#ekipe
@bottle.get('/ekipa/')
def isci_ekipo():
    iskalni_niz = bottle.request.query.getunicode('iskalni_niz')
    ekipe = list(Ekipa.poisci(""))
    if iskalni_niz:
        ekipe = [ekipa for ekipa in ekipe if iskalni_niz.lower() in ekipa.ime.lower()]
    return bottle.template('ekipa.html', iskalni_niz=iskalni_niz, ekipe=ekipe)


@bottle.get('/ekipa/<ime>/')
def voznik_in_leto_ekipe(ime):
    ekipe = list(Ekipa.poisci(ime))
    if not ekipe:
        return f"Ekipa {ime} ne obstaja!"
    ekipa = ekipe[0]
    vozniki = list(ekipa.poisci_voznike())
    return bottle.template('ekipa_vse.html', vozniki=vozniki, ekipa=ekipa)


@bottle.get('/ekipe/')
def lestvica_ekip():
    vse_ekipe = list(Ekipa.poisci(""))
    lestvica = []
    for ekipa in vse_ekipe:
        skupno, najboljsi_voznik = ekipa.poisci_skupne_tocke_in_najboljsi_voznik()
        lestvica.append((ekipa.ime, skupno, najboljsi_voznik))
    lestvica.sort(key=lambda x: x[1] or 0, reverse=True)
    return bottle.template('ekipe_lestvica.html', lestvica=lestvica)


#login in admin
@bottle.route('/login', method=['GET', 'POST'])
def login():
    if bottle.request.method == 'POST':
        username = bottle.request.forms.get('username')
        password = bottle.request.forms.get('password')
        if username == "admin" and password == "admin":
            response.set_cookie("admin", "true", secret=SECRET, path='/', httponly=True)
            return bottle.redirect('/admin')
        else:
            return "Napačno geslo!"
    return bottle.template('login.html')


@bottle.route('/admin')
def admin():
    if request.get_cookie("admin", secret=SECRET) != "true":
        return redirect('/login')

    conn = get_conn()
    cur = conn.cursor()

    # Države
    cur.execute("SELECT DISTINCT drzava FROM proga")
    drzave = [row[0] for row in cur.fetchall()]

    # Eventi
    cur.execute("""
        SELECT event.id, event.leto, proga.drzava
        FROM event
        JOIN proga ON event.id_proge = proga.id
        ORDER BY event.leto DESC
    """)
    eventi = cur.fetchall()

    # Rezultati po eventih
    rezultati_po_eventih = {}
    for e in eventi:
        event_id = e[0]
        cur.execute("""
            SELECT rezultat.id, voznik.ime_priimek, ekipa.ime, rezultat.mesto, rezultat.cas, rezultat.tocke
            FROM rezultat
            JOIN voznik ON rezultat.voznik_id = voznik.id
            JOIN ekipa ON rezultat.ekipa_id = ekipa.id
            WHERE rezultat.event_id = ?
            ORDER BY 
                CASE WHEN rezultat.mesto IS NULL THEN 1 ELSE 0 END,
                rezultat.mesto ASC
        """, (event_id,))
        rezultati_po_eventih[event_id] = cur.fetchall()

    # DOdamo voznike
    cur.execute("SELECT id, ime_priimek FROM voznik ORDER BY ime_priimek")
    vozniki = cur.fetchall()

    # Dodamo ekipe
    cur.execute("SELECT id, ime FROM ekipa ORDER BY ime")
    ekipe = cur.fetchall()

    conn.close()

    return bottle.template(
        'admin.html',
        drzave=drzave,
        eventi=eventi,
        rezultati_po_eventih=rezultati_po_eventih,
        vozniki=vozniki,
        ekipe=ekipe
    )


@bottle.post('/add_event')
def add_event():
    if request.get_cookie("admin", secret=SECRET) != "true":
        return redirect('/login')

    try:
        leto = int(request.forms.get('leto'))
    except (TypeError, ValueError):
        return "<p>Neveljavno leto!</p><a href='/admin'>Nazaj</a>"

    drzava = request.forms.get('drzava')

    conn = get_conn()
    cur = conn.cursor()

    # poišči progo
    cur.execute("SELECT id FROM proga WHERE drzava=?", (drzava,))
    proga = cur.fetchone()
    if not proga:
        conn.close()
        return f"<p>Država {drzava} ne obstaja v bazi!</p><a href='/admin'>Nazaj</a>"
    proga_id = proga[0]

    # preveri, če event že obstaja
    cur.execute("SELECT id FROM event WHERE leto=? AND id_proge=?", (leto, proga_id))
    obstaja = cur.fetchone()
    if obstaja:
        conn.close()
        return f"<p>Event za {drzava} {leto} že obstaja!</p><a href='/admin'>Nazaj</a>"

    cur.execute("INSERT INTO event (leto, id_proge, najhitrejsi_cas) VALUES (?, ?, NULL)", (leto, proga_id))
    conn.commit()
    conn.close()
    return redirect('/admin')


@bottle.get('/delete_event/<id:int>/')
def delete_event(id):
    if request.get_cookie("admin", secret=SECRET) != "true":
        return redirect('/login')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM event WHERE id=?", (id,))
    obstaja = cur.fetchone()
    if not obstaja:
        conn.close()
        return f"<p>Event z ID {id} ne obstaja!</p><a href='/admin'>Nazaj</a>"

    # Pobriši rezultate za ta event 
    cur.execute("DELETE FROM rezultat WHERE event_id = ?", (id,))
    cur.execute("DELETE FROM event WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')


@bottle.post('/add_rezultat')
def add_rezultat():
    if request.get_cookie("admin", secret=SECRET) != "true":
        return redirect('/login')

    try:
        event_id = int(request.forms.get('event_id'))
        voznik = (request.forms.get('voznik') or '').strip()
        ekipa = (request.forms.get('ekipa') or '').strip()
        mesto_raw = request.forms.get('mesto')
        mesto = int(mesto_raw) if mesto_raw else None
        cas_raw = request.forms.get('cas')
        cas = cas_raw.strip() if cas_raw else None
        tocke_raw = request.forms.get('tocke')
        tocke = int(tocke_raw) if tocke_raw else None
    except ValueError:
        return "<p>Neveljaven vnos (številke morajo biti pravilne)!</p><a href='/admin'>Nazaj</a>"

    if not voznik or not ekipa:
        return "<p>Voznik in ekipa sta obvezna!</p><a href='/admin'>Nazaj</a>"

    conn = get_conn()
    cur = conn.cursor()

    # PReveri event
    cur.execute("SELECT id FROM event WHERE id=?", (event_id,))
    if not cur.fetchone():
        conn.close()
        return f"<p>Event z ID {event_id} ne obstaja!</p><a href='/admin'>Nazaj</a>"

    # voznik
    cur.execute("SELECT id FROM voznik WHERE ime_priimek = ?", (voznik,))
    row = cur.fetchone()
    if row:
        voznik_id = row[0]
    else:
        cur.execute("INSERT INTO voznik (ime_priimek) VALUES (?)", (voznik,))
        voznik_id = cur.lastrowid

    # ekipa
    cur.execute("SELECT id FROM ekipa WHERE ime = ?", (ekipa,))
    row = cur.fetchone()
    if row:
        ekipa_id = row[0]
    else:
        cur.execute("INSERT INTO ekipa (ime) VALUES (?)", (ekipa,))
        ekipa_id = cur.lastrowid

    # rezultat
    cur.execute(
        """
        INSERT INTO rezultat (event_id, voznik_id, ekipa_id, mesto, tocke, cas)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (event_id, voznik_id, ekipa_id, mesto, tocke, cas)
    )

    conn.commit()
    conn.close()
    return redirect('/admin')


@bottle.get('/delete_rezultat/<id:int>/')
def delete_rezultat(id):
    if request.get_cookie("admin", secret=SECRET) != "true":
        return redirect('/login')

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM rezultat WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@bottle.get('/delete_voznik/<id:int>/')
def delete_voznik(id):
    if request.get_cookie("admin", secret=SECRET) != "true":
        return redirect('/login')

    conn = get_conn()
    cur = conn.cursor()

    # Najprej izbrišemo vse rezultate za tega voznika
    cur.execute("DELETE FROM rezultat WHERE voznik_id = ?", (id,))
    # Nato izbrišemo voznika
    cur.execute("DELETE FROM voznik WHERE id = ?", (id,))

    conn.commit()
    conn.close()
    return redirect('/admin')

@bottle.get('/delete_ekipa/<id:int>/')
def delete_ekipa(id):
    if request.get_cookie("admin", secret=SECRET) != "true":
        return redirect('/login')

    conn = get_conn()
    cur = conn.cursor()

    # Najprej izbrišemo vse rezultate za to ekipo
    cur.execute("DELETE FROM rezultat WHERE ekipa_id = ?", (id,))
    # Nato izbrišemo ekipo
    cur.execute("DELETE FROM ekipa WHERE id = ?", (id,))

    conn.commit()
    conn.close()
    return redirect('/admin')

bottle.run(debug=True, reloader=True)
