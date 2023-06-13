import sqlite3
from flask import Flask, render_template, request, redirect, jsonify, session, flash
from datetime import datetime

app = Flask(__name__)

app.secret_key = 'my_secret_key'

# Crear la tabla de usuarios si no existe
conn = sqlite3.connect('database.db')
conn.execute('''CREATE TABLE IF NOT EXISTS users 
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                password TEXT,
                name TEXT,
                surname TEXT);''')



conn.execute('''CREATE TABLE IF NOT EXISTS peticiones 
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tipo_peticion TEXT,
                descripcion TEXT,
                fecha TEXT,
                hora TEXT,
                estado TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id));''')




conn.execute('''CREATE TABLE IF NOT EXISTS pagos 
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                fecha TEXT,
                monto REAL,
                motivo TEXT,
                estado TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id));''')
#conn.execute('DROP TABLE IF EXISTS notificaciones')
conn.execute('''CREATE TABLE IF NOT EXISTS notificaciones 
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id INTEGER,
             titulo TEXT,
             fecha TEXT,
             hora TEXT,
             mensaje TEXT);''')


conn.close()





@app.route('/notificacionestest')
def mostrar_notificaciones():
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("SELECT * FROM notificaciones")
    notificaciones = cursor.fetchall()
    conn.close()
    
    return render_template('testeo.html', notificaciones=notificaciones)





# Página de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.json['email']
        password = request.json['password']
        name = request.json['nombre']
        surname = request.json['apellido']

        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO users (email, password, name, surname) VALUES (?, ?, ?, ?)", (email, password, name, surname))
        conn.commit()
        conn.close()

        return jsonify({'success': True})

    return render_template('register.html')

# Resto del código
@app.route('/')
def inicio():
    return render_template('inicio.html')


@app.route('/welcome')
def index():
    if 'user' not in session:
        # Manejar el caso cuando el usuario no ha iniciado sesión
        return redirect('/login')

    user_id = session['user']['id']
    conn = sqlite3.connect('database.db')
    cursor = conn.execute('SELECT name FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        # Manejar el caso cuando no se encuentra el usuario en la base de datos
        return "Usuario no encontrado"

    username = row[0]
    return render_template('welcome.html', username=username)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()
        conn.close()

        if user:
            # Almacenar los datos del usuario en la sesión
            session['user'] = {
                'id': user[0],
                'email': user[1],
                'name': user[3],
                'surname': user[4]
            }
            return redirect('/welcome')
        else:
            return render_template('login.html', error=True)

    return render_template('login.html')



@app.route('/peticiones')
def peticiones():
    if 'user' not in session:
        # Manejar el caso cuando el usuario no ha iniciado sesión
        return redirect('/login')

    user_id = session['user']['id']
    conn = sqlite3.connect('database.db')
    cursor = conn.execute('SELECT * FROM peticiones WHERE user_id=?', (user_id,))
    rows = cursor.fetchall()
    conn.close()

    peticiones = []
    for row in rows:
        peticion = {
            'id': row[0],
            'fecha': row[2],
            'tipo_peticion': row[3],
            'descripcion': row[4],
            'estado': row[5]
        }
        peticiones.append(peticion)

    return render_template('peticiones.html', rows=rows)







@app.route('/nueva_peticion', methods=['GET', 'POST'])
def nueva_peticion():
    if request.method == 'POST':
        # Obtener el user_id del registro de la base de datos del usuario que inició sesión
        if 'user' in session:
            user_id = session['user']['id']
        else:
            # Manejar el caso cuando el usuario no ha iniciado sesión
            return redirect('/login')

        tipo_peticion = request.form['tipo_peticion']
        descripcion = request.form['descripcion']
        fecha = datetime.now().strftime('%Y-%m-%d')  # Obtener la fecha actual
        hora = datetime.now().strftime('%H:%M:%S')  # Obtener la hora actual

        conn = sqlite3.connect('database.db')
        conn.execute("INSERT INTO peticiones (user_id, fecha, hora, tipo_peticion, descripcion, estado) VALUES (?, ?, ?, ?, ?, ?)",
                     (user_id, fecha, hora, tipo_peticion, descripcion, 'En curso'))  # Agregar 'En curso' como valor de estado
        conn.commit()

        # Actualizar el estado de la última petición a 'En curso'
        conn.execute("UPDATE peticiones SET estado = 'En curso' WHERE id = (SELECT MAX(id) FROM peticiones)")
        conn.commit()

        conn.close()

        return redirect('/peticiones')

    return render_template('nueva_peticion.html', current_date=datetime.now().strftime('%Y-%m-%d'), current_time=datetime.now().strftime('%H:%M:%S'))

@app.route('/actualizar_datos', methods=['POST'])
def actualizar_datos():
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    email = request.form['email']
    user_id = session['user']['id']

    # Actualizar los datos del usuario en la base de datos
    conn = sqlite3.connect('database.db')
    conn.execute("UPDATE users SET name=?, surname=?, email=? WHERE id=?", (nombre, apellido, email, user_id))
    conn.commit()
    conn.close()

    flash('Los datos han sido actualizados exitosamente.')
    return redirect('/mis_datos')



@app.route('/cambiar_contrasena', methods=['POST'])
def cambiar_contrasena():
    contrasena_actual = request.form['contrasena_actual']
    nueva_contrasena = request.form['nueva_contrasena']
    confirmar_contrasena = request.form['confirmar_contrasena']

    # Verificar si la contraseña actual coincide con la almacenada en la base de datos
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("SELECT password FROM users WHERE id=?", (session['user']['id'],))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        # Manejar el caso cuando el usuario no se encuentra en la base de datos
        flash('No se encontró al usuario en la base de datos.')
        return redirect('/mis_datos')

    contrasena_guardada = row[0]

    if contrasena_actual != contrasena_guardada:
        # Manejar el caso cuando la contraseña actual no coincide
        flash('La contraseña actual ingresada es incorrecta.')
        return redirect('/mis_datos')

    if nueva_contrasena != confirmar_contrasena:
        # Manejar el caso cuando la confirmación de contraseña no coincide
        flash('La confirmación de contraseña no coincide.')
        return redirect('/mis_datos')

    # Actualizar la contraseña en la base de datos
    conn = sqlite3.connect('database.db')
    conn.execute("UPDATE users SET password=? WHERE id=?", (nueva_contrasena, session['user']['id']))
    conn.commit()
    conn.close()

    flash('La contraseña ha sido cambiada exitosamente.')
    return redirect('/mis_datos')


@app.route('/mis_datos', methods=['GET'])
def mis_datos():
    if 'user' not in session:
        # Manejar el caso cuando el usuario no ha iniciado sesión
        return redirect('/login')

    user_id = session['user']['id']
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        # Manejar el caso cuando no se encuentra el usuario en la base de datos
        return "Usuario no encontrado"

    user = {
        'id': row[0],
        'email': row[1],
        'password': row[2],
        'name': row[3],
        'surname': row[4]
    }

    return render_template('mis_datos.html', user=user)




@app.route('/mis_pagos', methods=['GET'])
def mis_pagos():
    if 'user' not in session:
        # Manejar el caso cuando el usuario no ha iniciado sesión
        return redirect('/login')

    user_id = session['user']['id']
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("SELECT * FROM pagos WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    pagos = []
    for row in rows:
        pago = {
            'id': row[0],
            'fecha': row[2],
            'monto': row[3],
            'motivo': row[4],
            'estado': row[5]
        }
        pagos.append(pago)

    return render_template('mis_pagos.html', pagos=pagos)


@app.route('/nuevo_pago')
def nuevo_pago():
    return render_template('nuevo_pago.html')



@app.route('/silversb')
def silversb():
    return render_template('silversb.html')

@app.route('/goldsb')
def goldsb():
    return render_template('goldsb.html')

@app.route('/diamondsb')
def diamondsb():
    return render_template('diamondsb.html')


@app.route('/registersilver')
def registersilver():
    return render_template('registersilver.html')

@app.route('/registergold')
def registergold():
    return render_template('registergold.html')

@app.route('/registerdiamond')
def registerdiamond():
    return render_template('registerdiamond.html')





""""
ACA ABAJO TODO LO DE ADMIN
"""





@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Aquí puedes agregar la lógica de autenticación para el administrador
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect('/administrador')
        else:
            error = 'Credenciales incorrectas. Inténtalo de nuevo.'
            return render_template('admin/login_admin.html', error=error)

    return render_template('admin/login_admin.html')

@app.route('/administrador')
def administrador():
    if 'admin' not in session:
        return redirect('/login_admin')

    # Aquí puedes agregar la lógica para mostrar la página de administrador
    return render_template('admin/administrador.html')



@app.route('/admin_users', methods=['GET'])
def admin_users():
    conn = sqlite3.connect('database.db')
    cursor = conn.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    
    return render_template('admin/admin_users.html', users=users)

@app.route('/modificar_usuario', methods=['POST'])
def modificar_usuario():
    user_id = request.form['user_id']
    campo = request.form['campo']
    nuevo_valor = request.form['valor']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Verificar el campo seleccionado y actualizar el valor correspondiente en la base de datos
    if campo == 'password':
        cursor.execute("UPDATE users SET password=? WHERE id=?", (nuevo_valor, user_id))
    elif campo == 'email':
        cursor.execute("UPDATE users SET email=? WHERE id=?", (nuevo_valor, user_id))
    elif campo == 'nombre':
        cursor.execute("UPDATE users SET name=? WHERE id=?", (nuevo_valor, user_id))
    elif campo == 'apellido':
        cursor.execute("UPDATE users SET surname=? WHERE id=?", (nuevo_valor, user_id))
    # Agrega más condiciones según los campos que deseas modificar
    
    conn.commit()
    conn.close()

    return redirect('/admin_users')


@app.route('/admin_change_password', methods=['GET'])
def admin_change_password():
    conn = sqlite3.connect('database.db')
    cursor = conn.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    
    return render_template('admin/admin_change_password.html', users=users)


@app.route('/admin_pagos', methods=['GET'])
def admin_pagos():
    conn = sqlite3.connect('database.db')
    cursor = conn.execute('SELECT * FROM pagos')
    pagos = cursor.fetchall()
    conn.close()
    
    return render_template('admin/admin_pagos.html', pagos=pagos)

@app.route('/generar_pago', methods=['POST'])
def generar_pago():
    user_id = request.form['user_id']
    fecha = request.form['fecha']
    monto = request.form['monto']
    motivo = request.form['motivo']
    estado = 'Pendiente'  # Establece el estado predeterminado
     # Obtener la hora actual
    conn = sqlite3.connect('database.db')
    conn.execute('INSERT INTO pagos (user_id, fecha, monto, motivo, estado) VALUES (?, ?, ?, ?, ?)',
                 (user_id, fecha, monto, motivo, estado))
    conn.commit()

    # Crear una notificación relacionada con el nuevo pago
    titulo = 'Recibimos su pago'
    fecha = datetime.now().strftime('%Y-%m-%d')
    hora = datetime.now().strftime('%H:%M:%S')
    mensaje = f'Hemos recibido un nuevo pago con el monto de: $ {monto} . Muchas Gracias'

    conn.execute('INSERT INTO notificaciones (user_id, titulo, fecha, hora, mensaje) VALUES (?, ?, ?, ?, ?)',
                 (user_id, titulo, fecha, hora, mensaje))
    conn.commit()





    conn.close()
    
    return redirect('/admin_pagos')

@app.route('/cambiar_estado_pago', methods=['POST'])
def cambiar_estado_pago():
    pago_id = request.form['pago_id']
    nuevo_estado = request.form['estado']
    
    conn = sqlite3.connect('database.db')
    conn.execute("UPDATE pagos SET estado=? WHERE id=?", (nuevo_estado, pago_id))
    conn.commit()
    conn.close()
    
    return redirect('/admin_pagos')



@app.route('/admin_peticiones', methods=['GET'])
def admin_peticiones():
    conn = sqlite3.connect('database.db')
    cursor = conn.execute('SELECT p.id, p.tipo_peticion, p.descripcion, p.fecha, p.hora, p.estado, p.user_id, u.name, u.surname FROM peticiones p INNER JOIN users u ON p.user_id = u.id')
    peticiones = cursor.fetchall()
    conn.close()

    return render_template('admin/admin_peticiones.html', peticiones=peticiones)



@app.route('/cambiar_estado_peticion', methods=['POST'])
def cambiar_estado_peticion():
    peticion_id = request.form['peticion_id']
    nuevo_estado = request.form['estado']
    user_id = request.form['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    conn.execute('UPDATE peticiones SET estado=? WHERE id=?', (nuevo_estado, peticion_id))
    conn.commit()

    # Crear un registro en la tabla de notificaciones
    titulo = 'Novedades sobre tu peticion!'
    fecha = datetime.now().strftime('%Y-%m-%d')
    hora = datetime.now().strftime('%H:%M:%S')
    mensaje = f'Se ha modificado el estado de la petición con ID {peticion_id} a {nuevo_estado}'

    conn.execute('INSERT INTO notificaciones (user_id, titulo, fecha, hora, mensaje) VALUES (?, ?, ?, ?, ?)',
                 (user_id, titulo, fecha, hora, mensaje))
    conn.commit()

   
    conn.close()
    
    return redirect('/admin_peticiones')


from datetime import datetime

@app.route('/notificaciones', methods=['GET'])
def notificaciones():
    if 'user' not in session:
        # Manejar el caso cuando el usuario no ha iniciado sesión
        return redirect('/login')

    user_id = session['user']['id']
    conn = sqlite3.connect('database.db')
    cursor = conn.execute("SELECT fecha, hora, titulo, mensaje FROM notificaciones WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    notificaciones = []
    for row in rows:
        notificacion = {
            'fecha': row[0],
            'hora': row[1],  # Utilizamos el valor almacenado en la base de datos
            'titulo': row[2],
            'mensaje': row[3]
        }
        notificaciones.append(notificacion)

    return render_template('notificaciones.html', notificaciones=notificaciones)



if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=80)
