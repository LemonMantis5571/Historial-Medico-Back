from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector
from datetime import datetime
from db import app, db_config
import bcrypt
def hash_password(password):
    salt = bcrypt.gensalt() 
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')



@app.route('/usuarios', methods=['POST'])
@cross_origin()
def create_usuario():
    cursor = None
    connection = None
    try:
        user_data = request.get_json()
        app.logger.debug(f"Received user data: {user_data}")

        if not user_data:
            app.logger.error("No data provided in the request")
            return jsonify({'error': 'No data provided in the request'}), 400

        # Required fields for all users
        required_fields = ['nombre', 'correo', 'password', 'id_rol']
        missing_fields = [field for field in required_fields if field not in user_data]
        if missing_fields:
            app.logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Start transaction
        connection.start_transaction()

        # Verificar que el rol existe y obtener información del rol
        cursor.execute("SELECT COUNT(*), (SELECT Nombre FROM Rol WHERE ID_Rol = %s) FROM Rol WHERE ID_Rol = %s", 
                      (user_data['id_rol'], user_data['id_rol']))
        rol_result = cursor.fetchone()
        if rol_result[0] == 0:
            return jsonify({'error': 'Rol no encontrado'}), 404
        
        rol_name = rol_result[1].lower() if rol_result[1] else ""

        # Verificar que el correo no esté duplicado
        cursor.execute("SELECT COUNT(*) FROM Usuario WHERE Correo = %s", (user_data['correo'],))
        if cursor.fetchone()[0] > 0:
            return jsonify({'error': 'El correo ya está registrado'}), 409

        id_paciente = None
        id_medico = None

        # Create Paciente record if role is patient
        if 'paciente' in rol_name or user_data['id_rol'] == 1:  # Assuming rol 1 is paciente
            # Required fields for paciente
            paciente_required = ['fecha_nacimiento', 'genero', 'telefono']
            missing_paciente = [field for field in paciente_required if field not in user_data]
            if missing_paciente:
                return jsonify({'error': f'Missing required fields for paciente: {", ".join(missing_paciente)}'}), 400

            paciente_query = """
            INSERT INTO Paciente (Nombre, Fecha_Nacimiento, Género, Teléfono)
            VALUES (%s, %s, %s, %s)
            """
            paciente_values = (
                user_data['nombre'],
                user_data['fecha_nacimiento'],
                user_data['genero'],
                user_data['telefono']
            )
            
            cursor.execute(paciente_query, paciente_values)
            id_paciente = cursor.lastrowid
            
            # Create historial_medico for paciente
            historial_query = "INSERT INTO historial_medico (ID_Paciente, Fecha_Creación) VALUES (%s, NOW())"
            cursor.execute(historial_query, (id_paciente,))
            
            app.logger.info(f"Created Paciente record with ID: {id_paciente}")
            app.logger.info(f"Created historial_medico for paciente: {id_paciente}")

        # Create Médico record if role is doctor
        elif 'medico' in rol_name or 'doctor' in rol_name or user_data['id_rol'] == 2:  # Assuming rol 2 is médico
            # Required fields for médico
            medico_required = ['especialidad', 'telefono']
            missing_medico = [field for field in medico_required if field not in user_data]
            if missing_medico:
                return jsonify({'error': f'Missing required fields for médico: {", ".join(missing_medico)}'}), 400

            medico_query = """
            INSERT INTO Médico (Nombre, Especialidad, Teléfono)
            VALUES (%s, %s, %s)
            """
            medico_values = (
                user_data['nombre'],
                user_data['especialidad'],
                user_data['telefono']
            )
            
            cursor.execute(medico_query, medico_values)
            id_medico = cursor.lastrowid
            
            app.logger.info(f"Created Médico record with ID: {id_medico}")

        # Create Usuario record
        usuario_query = """
        INSERT INTO Usuario (Nombre, Correo, Contraseña, ID_Rol, ID_Paciente, ID_Doctor)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        app.logger.debug(f"Hashing password for user: {user_data['nombre']}")
        hashed_password = hash_password(user_data['password'])

        usuario_values = (
            user_data['nombre'],
            user_data['correo'],
            hashed_password,
            user_data['id_rol'],
            id_paciente,
            id_medico
        )

        app.logger.debug(f"Executing usuario query: {usuario_query}")
        app.logger.debug(f"Usuario values: {usuario_values}")

        cursor.execute(usuario_query, usuario_values)
        usuario_id = cursor.lastrowid

        # Commit transaction
        connection.commit()

        app.logger.info(f"User {user_data['nombre']} created successfully with ID: {usuario_id}")
        
        response_data = {
            'message': 'Usuario creado exitosamente',
            'usuario_id': usuario_id,
            'nombre': user_data['nombre'],
            'correo': user_data['correo'],
            'id_rol': user_data['id_rol']
        }
        
        if id_paciente:
            response_data['id_paciente'] = id_paciente
            response_data['tipo'] = 'paciente'
        
        if id_medico:
            response_data['id_medico'] = id_medico
            response_data['tipo'] = 'medico'
            
        return jsonify(response_data), 201

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()
        app.logger.error(f"Database error: {error}")
        app.logger.debug("Error details:", exc_info=True)
        return jsonify({'error': f'Database error: {str(error)}'}), 500

    except Exception as e:
        if connection:
            connection.rollback()
        app.logger.error(f"Unexpected error: {str(e)}")
        app.logger.debug("Error details:", exc_info=True)
        return jsonify({'error': f'Unexpected error occurred: {str(e)}'}), 500

    finally:
        try:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        except Exception as cleanup_error:
            app.logger.error(f"Error closing database connection: {str(cleanup_error)}")
            app.logger.debug("Cleanup error details:", exc_info=True)


# Helper endpoint to get user details with related data
@app.route('/usuarios/<int:user_id>', methods=['GET'])
@cross_origin()
def get_usuario(user_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Get user basic info
        cursor.execute("""
            SELECT u.*, r.Nombre as rol_nombre 
            FROM Usuario u 
            JOIN Rol r ON u.ID_Rol = r.ID_Rol 
            WHERE u.ID_Usuario = %s
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404

        # Get paciente details if applicable
        if user['ID_Paciente']:
            cursor.execute("SELECT * FROM Paciente WHERE ID_Paciente = %s", (user['ID_Paciente'],))
            paciente_data = cursor.fetchone()
            user['paciente_details'] = paciente_data

        # Get médico details if applicable
        if user['ID_Doctor']:
            cursor.execute("SELECT * FROM Médico WHERE ID_Médico = %s", (user['ID_Doctor'],))
            medico_data = cursor.fetchone()
            user['medico_details'] = medico_data

        # Remove password from response
        user.pop('Contraseña', None)

        return jsonify(user), 200

    except mysql.connector.Error as error:
        app.logger.error(f"Database error: {error}")
        return jsonify({'error': f'Database error: {str(error)}'}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Unexpected error occurred: {str(e)}'}), 500

    finally:
        try:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        except Exception as cleanup_error:
            app.logger.error(f"Error closing database connection: {str(cleanup_error)}")


# Endpoint to update user relationships (assign patient to doctor, etc.)
@app.route('/usuarios/<int:user_id>/assign-doctor', methods=['PUT'])
@cross_origin()
def assign_doctor_to_patient(user_id):
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data or 'id_doctor' not in data:
            return jsonify({'error': 'ID del doctor requerido'}), 400

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Verify patient user exists and has a paciente record
        cursor.execute("""
            SELECT ID_Paciente FROM Usuario 
            WHERE ID_Usuario = %s AND ID_Paciente IS NOT NULL
        """, (user_id,))
        
        patient = cursor.fetchone()
        if not patient:
            return jsonify({'error': 'Usuario paciente no encontrado'}), 404

        # Verify doctor exists
        cursor.execute("""
            SELECT ID_Doctor FROM Usuario 
            WHERE ID_Usuario = %s AND ID_Doctor IS NOT NULL
        """, (data['id_doctor'],))
        
        if not cursor.fetchone():
            return jsonify({'error': 'Usuario médico no encontrado'}), 404

        # Update the patient's assigned doctor
        cursor.execute("""
            UPDATE Usuario 
            SET ID_Doctor = %s 
            WHERE ID_Usuario = %s
        """, (data['id_doctor'], user_id))
        
        connection.commit()

        return jsonify({
            'message': 'Doctor asignado exitosamente',
            'patient_id': user_id,
            'doctor_id': data['id_doctor']
        }), 200

    except mysql.connector.Error as error:
        if connection:
            connection.rollback()
        app.logger.error(f"Database error: {error}")
        return jsonify({'error': f'Database error: {str(error)}'}), 500

    except Exception as e:
        if connection:
            connection.rollback()
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': f'Unexpected error occurred: {str(e)}'}), 500

    finally:
        try:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        except Exception as cleanup_error:
            app.logger.error(f"Error closing database connection: {str(cleanup_error)}")
            
@app.route('/usuarios/<int:usuario_id>', methods=['PUT'])
@jwt_required()
@cross_origin()
def update_usuario(usuario_id):
    cursor = None
    connection = None
    try:
        user_data = request.get_json()
        
        if not user_data:
            return jsonify({'error': 'No data provided'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT COUNT(*) FROM Usuario WHERE ID_Usuario = %s", (usuario_id,))
        if cursor.fetchone()[0] == 0:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Construir query dinámicamente según los campos proporcionados
        update_fields = []
        values = []
        
        if 'nombre' in user_data:
            update_fields.append("Nombre = %s")
            values.append(user_data['nombre'])
            
        if 'correo' in user_data:
            # Verificar que el correo no esté duplicado por otro usuario
            cursor.execute("SELECT COUNT(*) FROM Usuario WHERE Correo = %s AND ID_Usuario != %s", 
                         (user_data['correo'], usuario_id))
            if cursor.fetchone()[0] > 0:
                return jsonify({'error': 'El correo ya está registrado por otro usuario'}), 409
            update_fields.append("Correo = %s")
            values.append(user_data['correo'])
            
        if 'password' in user_data:
            hashed_password = hash_password(user_data['password'])
            update_fields.append("Contraseña = %s")
            values.append(hashed_password)
            
        if 'id_rol' in user_data:
            # Verificar que el rol existe
            cursor.execute("SELECT COUNT(*) FROM Rol WHERE ID_Rol = %s", (user_data['id_rol'],))
            if cursor.fetchone()[0] == 0:
                return jsonify({'error': 'Rol no encontrado'}), 404
            update_fields.append("ID_Rol = %s")
            values.append(user_data['id_rol'])
        
        if not update_fields:
            return jsonify({'error': 'No hay campos para actualizar'}), 400
        
        values.append(usuario_id)
        query = f"UPDATE Usuario SET {', '.join(update_fields)} WHERE ID_Usuario = %s"
        
        cursor.execute(query, values)
        connection.commit()
        
        return jsonify({'message': 'Usuario actualizado exitosamente'})
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/usuarios/<int:usuario_id>', methods=['DELETE'])
@jwt_required()
@cross_origin()
def delete_usuario(usuario_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT COUNT(*) FROM Usuario WHERE ID_Usuario = %s", (usuario_id,))
        if cursor.fetchone()[0] == 0:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        query = "DELETE FROM Usuario WHERE ID_Usuario = %s"
        cursor.execute(query, (usuario_id,))
        connection.commit()
        
        return jsonify({'message': 'Usuario eliminado exitosamente'})
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()