from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector  
from db import app, db_config
from datetime import datetime




@app.route('/pacientes', methods=['POST'])
@cross_origin()
def create_paciente():
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['nombre', 'fecha_nacimiento', 'genero', 'telefono']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        query = """
        INSERT INTO Paciente (Nombre, Fecha_Nacimiento, Género, Teléfono)
        VALUES (%s, %s, %s, %s)
        """
        
        values = (data['nombre'], data['fecha_nacimiento'], data['genero'], data['telefono'])
        cursor.execute(query, values)
        connection.commit()
        
        return jsonify({'message': 'Paciente creado exitosamente', 'id': cursor.lastrowid}), 201
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error: {error}")
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Unexpected error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/pacientes', methods=['GET'])
@cross_origin()
def get_pacientes():
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM Paciente ORDER BY Nombre"
        cursor.execute(query)
        pacientes = cursor.fetchall()
        
        # Convertir dates a string para JSON
        for paciente in pacientes:
            if paciente['Fecha_Nacimiento']:
                paciente['Fecha_Nacimiento'] = paciente['Fecha_Nacimiento'].strftime('%Y-%m-%d')
        
        return jsonify(pacientes)
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/patients/<int:patient_id>', methods=['GET'])
@cross_origin()
def get_patient(patient_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT 
            ID_Paciente,
            Nombre,
            Fecha_Nacimiento,
            Género,
            Teléfono
        FROM Paciente 
        WHERE ID_Paciente = %s
        """
        cursor.execute(query, (patient_id,))
        patient = cursor.fetchone()
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
      
        age = None
        if patient['Fecha_Nacimiento']:
            from datetime import date
            today = date.today()
            birth_date = patient['Fecha_Nacimiento']
            
            age = today.year - birth_date.year
            if (today.month, today.day) < (birth_date.month, birth_date.day):
                age -= 1
        
        # Translate gender to English
        gender_map = {
            'Masculino': 'Male',
            'Femenino': 'Female',
            'Otro': 'Other'
        }
        
        # Build response with English field names
        response = {
            'patientId': patient['ID_Paciente'],
            'name': patient['Nombre'],
            'birthDate': patient['Fecha_Nacimiento'].strftime('%Y-%m-%d') if patient['Fecha_Nacimiento'] else None,
            'gender': gender_map.get(patient['Género'], patient['Género']),  # Default to original if not in map
            'phone': patient['Teléfono'],
            'age': age
        }
        
        return jsonify(response)
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error in get_patient: {error}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in get_patient: {e}")
        return jsonify({'error': 'Unexpected error'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/pacientes/<int:paciente_id>', methods=['PUT'])
@cross_origin()
def update_paciente(paciente_id):
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Check if at least one updatable field is provided
        updatable_fields = ['nombre', 'fecha_nacimiento', 'genero', 'telefono']
        if not any(field in data for field in updatable_fields):
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # First check if the patient exists
        cursor.execute("SELECT ID_Paciente FROM Paciente WHERE ID_Paciente = %s", (paciente_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Paciente not found'}), 404
        
        # Build the update query dynamically based on provided fields
        set_clauses = []
        values = []
        
        if 'nombre' in data:
            set_clauses.append("Nombre = %s")
            values.append(data['nombre'])
        if 'fecha_nacimiento' in data:
            set_clauses.append("Fecha_Nacimiento = %s")
            values.append(data['fecha_nacimiento'])
        if 'genero' in data:
            set_clauses.append("Género = %s")
            values.append(data['genero'])
        if 'telefono' in data:
            set_clauses.append("Teléfono = %s")
            values.append(data['telefono'])
        
        # Add the paciente_id to the values for the WHERE clause
        values.append(paciente_id)
        
        query = f"""
        UPDATE Paciente
        SET {', '.join(set_clauses)}
        WHERE ID_Paciente = %s
        """
        
        cursor.execute(query, values)
        connection.commit()
        
        # Get the updated patient data to return
        cursor.execute("""
        SELECT ID_Paciente, Nombre, Fecha_Nacimiento, Género, Teléfono 
        FROM Paciente 
        WHERE ID_Paciente = %s
        """, (paciente_id,))
        updated_paciente = cursor.fetchone()
        
        return jsonify({
            'message': 'Paciente actualizado exitosamente',
            'paciente': updated_paciente
        }), 200
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error: {error}")
        connection.rollback()
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Unexpected error occurred'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()