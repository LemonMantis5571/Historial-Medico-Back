from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required
from flask_cors import cross_origin
import mysql.connector
from datetime import datetime
from datetime import date
from db import app, db_config

@app.route('/medicos', methods=['POST'])
@jwt_required()
@cross_origin()
def create_medico():
    cursor = None
    connection = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['nombre', 'especialidad', 'telefono']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400
        
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        query = """
        INSERT INTO Médico (Nombre, Especialidad, Teléfono)
        VALUES (%s, %s, %s)
        """
        
        values = (data['nombre'], data['especialidad'], data['telefono'])
        cursor.execute(query, values)
        connection.commit()
        
        return jsonify({'message': 'Médico creado exitosamente', 'id': cursor.lastrowid}), 201
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route('/medicos', methods=['GET'])
@jwt_required()
@cross_origin()
def get_medicos():
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        query = "SELECT * FROM Médico ORDER BY Nombre"
        cursor.execute(query)
        medicos = cursor.fetchall()
        
        return jsonify({'medicos': medicos})
        
    except mysql.connector.Error as error:
        return jsonify({'error': f'Database error: {str(error)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/medicos/<int:medico_id>/pacientes', methods=['GET'])
@cross_origin()
def get_patients_by_doctor(medico_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        # First verify the doctor exists
        cursor.execute("SELECT ID_Médico FROM Médico WHERE ID_Médico = %s", (medico_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Doctor not found'}), 404
        
        query = """
        SELECT DISTINCT
            p.ID_Paciente,
            p.Nombre,
            p.Fecha_Nacimiento,
            p.Género,
            p.Teléfono,
            COUNT(c.ID_Cita) AS total_citas
        FROM Paciente p
        JOIN Cita c ON p.ID_Paciente = c.ID_Paciente
        WHERE c.ID_Médico = %s
        GROUP BY p.ID_Paciente
        ORDER BY p.Nombre
        """
        cursor.execute(query, (medico_id,))
        patients = cursor.fetchall()
        
        # Process each patient
        result = []
        today = date.today()
        
        for patient in patients:
            # Calculate age
            age = None
            if patient['Fecha_Nacimiento']:
                birth_date = patient['Fecha_Nacimiento']
                age = today.year - birth_date.year
                if (today.month, today.day) < (birth_date.month, birth_date.day):
                    age -= 1
            
            # Translate gender
            gender_map = {
                'Masculino': 'Male',
                'Femenino': 'Female',
                'Otro': 'Other'
            }
            
            result.append({
                'patientId': patient['ID_Paciente'],
                'name': patient['Nombre'],
                'birthDate': patient['Fecha_Nacimiento'].strftime('%Y-%m-%d') if patient['Fecha_Nacimiento'] else None,
                'gender': gender_map.get(patient['Género'], patient['Género']),
                'phone': patient['Teléfono'],
                'age': age,
                'appointmentCount': patient['total_citas']
            })
        
        return jsonify({
            'success': True,
            'medicoId': medico_id,
            'patients': result,
            'count': len(result)
        })
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error in get_patients_by_doctor: {error}")
        return jsonify({'error': 'Database error'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in get_patients_by_doctor: {e}")
        return jsonify({'error': 'Unexpected error'}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/medicos/<int:medico_id>', methods=['GET'])
@cross_origin()
def get_medico(medico_id):
    cursor = None
    connection = None
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT 
            ID_Médico as doctorId,
            Nombre as name,
            Especialidad as specialty,
            Teléfono as phone
        FROM Médico 
        WHERE ID_Médico = %s
        """
        cursor.execute(query, (medico_id,))
        medico = cursor.fetchone()
        
        if not medico:
            return jsonify({
                'success': False,
                'error': 'Doctor not found'
            }), 404
        
        return jsonify({
            'success': True,
            'medico': medico
        })
        
    except mysql.connector.Error as error:
        app.logger.error(f"Database error in get_medico: {error}")
        return jsonify({
            'success': False,
            'error': 'Database error'
        }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in get_medico: {e}")
        return jsonify({
            'success': False,
            'error': 'Unexpected error'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            


@app.route('/medicos/<int:medico_id>', methods=['PUT'])
@cross_origin()
def update_medico(medico_id):
    cursor = None
    connection = None
    try:
        # Get and validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields (removed email since it doesn't exist in the table)
        required_fields = ['name', 'specialty', 'phone']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        # Verify doctor exists
        cursor.execute("SELECT ID_Médico FROM Médico WHERE ID_Médico = %s", (medico_id,))
        if not cursor.fetchone():
            return jsonify({
                'success': False,
                'error': 'Doctor not found'
            }), 404

        # Update doctor information (removed Correo field)
        update_query = """
        UPDATE Médico 
        SET 
            Nombre = %s,
            Especialidad = %s,
            Teléfono = %s
        WHERE ID_Médico = %s
        """
        values = (
            data['name'],
            data['specialty'],
            data['phone'],
            medico_id
        )
        
        cursor.execute(update_query, values)
        connection.commit()

        # Get the updated doctor record (removed email from SELECT)
        cursor.execute("""
        SELECT 
            ID_Médico as doctorId,
            Nombre as name,
            Especialidad as specialty,
            Teléfono as phone
        FROM Médico 
        WHERE ID_Médico = %s
        """, (medico_id,))
        
        updated_medico = cursor.fetchone()

        return jsonify({
            'success': True,
            'message': 'Doctor updated successfully',
            'medico': updated_medico
        }), 200

    except mysql.connector.Error as error:
        app.logger.error(f"Database error updating doctor: {str(error)}")
        if connection:
            connection.rollback()
        return jsonify({
            'success': False,
            'error': 'Database operation failed',
            'details': str(error)
        }), 500
    except Exception as e:
        app.logger.error(f"Unexpected error updating doctor: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()