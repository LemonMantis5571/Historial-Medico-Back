from db import app, db_config
from flask_cors import cross_origin
from flask import jsonify, request
import mysql.connector
import bcrypt
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, exceptions
)
from datetime import timedelta

def verify_password(plain_password, hashed_password):
    """Verifica si la contraseña coincide con el hash"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        app.logger.error(f"Error verifying password: {e}")
        return False

@app.route('/api/auth/login', methods=['POST'])
@cross_origin()
def login():
    cursor = None
    connection = None
    try:
        login_data = request.get_json()
        app.logger.debug(f"Login attempt for user: {login_data.get('username', 'unknown')}")

        if not login_data:
            app.logger.error("No login data provided")
            return jsonify({'error': 'No data provided in the request'}), 400

        required_fields = ['username', 'password']
        missing_fields = [field for field in required_fields if field not in login_data]
        if missing_fields:
            app.logger.error(f"Missing required fields: {missing_fields}")
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        username = login_data['username']
        password = login_data['password']

        # Verificar credenciales en la tabla de usuarios
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        user_query = """
        SELECT u.*, r.Nombre as rol_nombre 
        FROM Usuario u 
        JOIN Rol r ON u.ID_Rol = r.ID_Rol 
        WHERE u.Correo = %s
        """
        cursor.execute(user_query, (username,))
        user = cursor.fetchone()

        if not user:
            app.logger.warning(f"User not found: {username}")
            return jsonify({'error': 'Invalid credentials'}), 401

        # Verificar contraseña
        if not verify_password(password, user['Contraseña']):
            app.logger.warning(f"Invalid password for user: {username}")
            return jsonify({'error': 'Invalid credentials'}), 401

        app.logger.info(f"User authenticated successfully: {username}")

        # Determine user type based on database fields
        user_type = 'generic'
        if user['ID_Paciente'] is not None:
            user_type = 'patient'
        elif user['ID_Doctor'] is not None:
            user_type = 'doctor'

        # Build user profile based on type
        user_profile = {
            'id': str(user['ID_Usuario']),
            'name': user['Nombre'],
            'email': username,
            'type': user_type,
            'role': user['rol_nombre']
        }

        app.logger.debug(f"User type: {user_type}, Role: {user['rol_nombre']}, ID_Paciente: {user['ID_Paciente']}")

        # Add additional fields based on user type (use user_type instead of rol_nombre)
        if user_type == 'patient' and user['ID_Paciente']:
            # Get patient details
            paciente_query = """
            SELECT Fecha_Nacimiento, Género, Teléfono
            FROM Paciente 
            WHERE ID_Paciente = %s
            """
            cursor.execute(paciente_query, (user['ID_Paciente'],))
            paciente = cursor.fetchone()
            
            app.logger.debug(f"Paciente data: {paciente}")
            
            if paciente:
                # Calculate age if birth date exists
                age = None
                if paciente['Fecha_Nacimiento']:
                    from datetime import date
                    today = date.today()
                    birth_date = paciente['Fecha_Nacimiento']
                    
                    # Handle both date and datetime objects
                    if hasattr(birth_date, 'date'):
                        birth_date = birth_date.date()
                    
                    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    app.logger.debug(f"Calculated age: {age} from birth date: {birth_date}")
                
                user_profile.update({
                    'age': age,
                    'gender': paciente['Género'],
                    'contact': paciente['Teléfono'],
                    'birth_date': str(paciente['Fecha_Nacimiento']) if paciente['Fecha_Nacimiento'] else None
                })

        elif user_type == 'doctor' and user['ID_Doctor']:
            # Get doctor details
            medico_query = """
            SELECT Especialidad, Teléfono
            FROM Médico 
            WHERE ID_Médico = %s
            """
            cursor.execute(medico_query, (user['ID_Doctor'],))
            medico = cursor.fetchone()
            
            app.logger.debug(f"Medico data: {medico}")
            
            if medico:
                user_profile.update({
                    'specialty': medico['Especialidad'],
                    'contact': medico['Teléfono'],
                    "ID_Doctor": user['ID_Doctor']
                })

        # Create JWT token
        additional_claims = {
            'user_id': user['ID_Usuario'],
            'user_type': user_type,
            'role': user['rol_nombre']
        }
        
        access_token = create_access_token(
            identity=username,
            additional_claims=additional_claims
        )

        app.logger.info(f"Login successful for user: {username}, type: {user_type}")
        app.logger.debug(f"Final user profile: {user_profile}")
        
        return jsonify({
            'token': access_token,
            'user': user_profile,
            'message': 'Login successful'
        }), 200

    except mysql.connector.Error as error:
        app.logger.error(f"Database error during login: {error}")
        app.logger.debug("Database error details:", exc_info=True)
        return jsonify({'error': 'Database connection error'}), 500

    except Exception as e:
        app.logger.error(f"Unexpected error during login: {str(e)}")
        app.logger.debug("Login error details:", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred'}), 500

    finally:
        # Close all connections
        try:
            if cursor:
                cursor.close()
            if connection:
                connection.close()
        except Exception as cleanup_error:
            app.logger.error(f"Error closing database connections: {str(cleanup_error)}")

# Endpoint adicional para obtener información del usuario actual
@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
@cross_origin()
def get_current_user():
    from flask_jwt_extended import get_jwt_identity, get_jwt
    
    try:
        current_user_email = get_jwt_identity()
        claims = get_jwt()
        
        user_info = {
            'email': current_user_email,
            'user_id': claims.get('user_id'),
            'user_type': claims.get('user_type'),
            'role': claims.get('role')
        }
        
        return jsonify({'user': user_info}), 200
        
    except Exception as e:
        app.logger.error(f"Error getting current user: {str(e)}")
        return jsonify({'error': 'Could not retrieve user information'}), 500

# Endpoint para logout (opcional, para invalidar token del lado del cliente)
@app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
@cross_origin()
def logout():
    try:
        # En una implementación real, podrías mantener una lista negra de tokens
        # Por ahora, simplemente confirmamos el logout
        app.logger.info("User logged out successfully")
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        app.logger.error(f"Error during logout: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500