import os
from flask import Flask, request, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or os.urandom(24).hex()

# Configuración de la base de datos SOLO para jugadores
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelo SOLO para jugadores
class Jugador(db.Model):
    __tablename__ = 'jugadores'
    Dorsal = db.Column(db.String(10), primary_key=True)
    Nombre = db.Column(db.String(100), nullable=False)
    Ap_paterno = db.Column(db.String(100), nullable=False)
    Ap_materno = db.Column(db.String(100))
    Edad_en_años = db.Column(db.Integer, nullable=False)
    Equipo = db.Column(db.String(50), nullable=False)

with app.app_context():
    db.create_all()
# Usuarios predefinidos EN MEMORIA (solo admin ahora)
USUARIOS = {
    "admin": {
        "password": generate_password_hash("admin123"),
        "rol": "admin"
    }
}

# Lista global de equipos disponibles
EQUIPOS_DISPONIBLES = [
    "Cracker's", "Barcelona", "Real Madrid", "Manchester United",
    "Bayern Múnich", "Juventus", "PSG"
]

# Decorador para verificar roles
def requiere_rol(rol):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if rol == 'admin' and ('username' not in session or USUARIOS.get(session['username'], {}).get('rol') != rol):
                flash('Acceso denegado: Se requieren credenciales de administrador', 'danger')
                return redirect(url_for('admin_login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Ruta para ingresar como invitado
@app.route('/entrar_como_invitado')
def entrar_como_invitado():
    session.clear()
    session['user_rol'] = 'invitado'
    flash('Has entrado como invitado. Solo puedes ver la información.', 'info')
    return redirect(url_for('index'))

# Ruta de login solo para admin
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'username' in session and USUARIOS.get(session['username'], {}).get('rol') == 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = USUARIOS.get(username)
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['user_rol'] = user['rol']
            flash('¡Bienvenido Administrador!', 'success')
            return redirect(url_for('index'))
        
        flash('Credenciales incorrectas', 'danger')
    
    return render_template('admin_login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('index'))

# Ruta principal
@app.route('/')
def index():
    # Si no hay sesión activa, redirigir a la página de selección
    if 'user_rol' not in session:
        return render_template('seleccion_entrada.html')
    
    jugadores = Jugador.query.order_by(Jugador.Equipo, Jugador.Dorsal).all()
    return render_template('index.html', 
                         jugadores=jugadores,
                         es_admin=session.get('user_rol') == 'admin')

# Rutas CRUD para jugadores (usa base de datos)
@app.route('/jugadores/new', methods=['GET', 'POST'])
@requiere_rol('admin')
def create_jugador():
    if request.method == 'POST':
        try:
            # Verificar si el dorsal ya existe
            if Jugador.query.filter_by(Dorsal=request.form.get('Dorsal')).first():
                flash('Ya existe un jugador con este dorsal', 'danger')
                return render_template('create_jugador.html', equipos=EQUIPOS_DISPONIBLES)
            
            nuevo_jugador = Jugador(
                Dorsal=request.form.get('Dorsal'),
                Nombre=request.form.get('Nombre'),
                Ap_paterno=request.form.get('Ap_paterno'),
                Ap_materno=request.form.get('Ap_materno', ''),
                Edad_en_años=int(request.form.get('Edad_en_años')),
                Equipo=request.form.get('Equipo')
            )
            
            db.session.add(nuevo_jugador)
            db.session.commit()
            flash('Jugador creado exitosamente', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear jugador: {str(e)}', 'danger')
    
    return render_template('create_jugador.html', equipos=EQUIPOS_DISPONIBLES)

@app.route('/jugadores/delete/<string:Dorsal>')
@requiere_rol('admin')
def delete_jugador(Dorsal):
    try:
        jugador = Jugador.query.get(Dorsal)
        if not jugador:
            flash('Jugador no encontrado', 'danger')
            return redirect(url_for('index'))
            
        db.session.delete(jugador)
        db.session.commit()
        flash('Jugador eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar jugador: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/jugadores/update/<string:Dorsal>', methods=['GET', 'POST'])
@requiere_rol('admin')
def update_jugador(Dorsal):
    jugador = Jugador.query.get(Dorsal)
    
    if not jugador:
        flash('Jugador no encontrado', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            jugador.Nombre = request.form.get('Nombre')
            jugador.Ap_paterno = request.form.get('Ap_paterno')
            jugador.Ap_materno = request.form.get('Ap_materno', '')
            jugador.Edad_en_años = int(request.form.get('Edad_en_años'))
            jugador.Equipo = request.form.get('Equipo')
            
            db.session.commit()
            flash('Jugador actualizado exitosamente', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar jugador: {str(e)}', 'danger')
    
    return render_template('update_jugador.html', 
                         jugador=jugador,
                         equipos=EQUIPOS_DISPONIBLES)

# Crear tablas SOLO de jugadores al iniciar
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)