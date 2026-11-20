import '../../../core/models/page_result.dart';
import '../../../core/network/api_client.dart';

class DoctorApi {
  DoctorApi(this.client);
  final ApiClient client;

  Future<Map<String, dynamic>?> doctorProfile() async {
    final doctors = await client.getList('medicos/');
    return doctors.isEmpty ? null : doctors.first;
  }

  Future<PageResult> patients({String search = '', int page = 1}) async {
    final data = await client.getMap(
      'pacientes/',
      query: {
        'page': page,
        'page_size': 100,
        if (search.trim().isNotEmpty) 'search': search.trim(),
      },
    );
    return PageResult(
      count: (data['count'] as num? ?? 0).toInt(),
      results: (data['results'] as List? ?? const [])
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList(),
    );
  }

  Future<List<Map<String, dynamic>>> schedules() => client.getList('horarios/');

  Future<Map<String, dynamic>> createSchedule({
    required int weekday,
    required String start,
    required String end,
  }) => client.postMap(
    'horarios/',
    data: {'dia_semana': weekday, 'hora_inicio': start, 'hora_fin': end},
  );

  Future<Map<String, dynamic>> updateSchedule(
    int id, {
    required int weekday,
    required String start,
    required String end,
  }) async {
    final response = await client.dio.put<dynamic>(
      'horarios/$id/',
      data: {'dia_semana': weekday, 'hora_inicio': start, 'hora_fin': end},
    );
    if (response.data is Map<String, dynamic>) {
      return response.data as Map<String, dynamic>;
    }
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<void> deleteSchedule(int id) =>
      client.dio.delete<void>('horarios/$id/');

  Future<PageResult> agenda({
    required String date,
    String? state,
    int page = 1,
  }) async {
    final data = await client.getMap(
      'citas/mi-agenda/',
      query: {
        'fecha': date,
        'page': page,
        'page_size': 100,
        if (state != null && state.isNotEmpty) 'estado': state,
      },
    );
    return PageResult(
      count: (data['count'] as num? ?? 0).toInt(),
      results: (data['results'] as List? ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList(),
    );
  }

  Future<Map<String, dynamic>> createConsultation({
    required int appointmentId,
    required String reason,
    required String notes,
    required String diagnosis,
  }) => client.postMap(
    'consultas/',
    data: {
      'cita_id': appointmentId,
      'motivo': reason,
      'observacion': notes,
      'diagnostico': diagnosis,
    },
  );

  Future<Map<String, dynamic>> consultation(int id) =>
      client.getMap('consultas/$id/');

  Future<Map<String, dynamic>> createPrescription(
    int consultationId, {
    required String instructions,
    required List<Map<String, String>> medicines,
  }) => client.postMap(
    'consultas/$consultationId/recetas/',
    data: {'indicaciones': instructions, 'medicamentos': medicines},
  );

  Future<Map<String, dynamic>> prescription(int id) =>
      client.getMap('recetas/$id/');

  Future<Map<String, dynamic>> patientHistory(int patientId, {int page = 1}) =>
      client.getMap(
        'pacientes/$patientId/historial-consultas/',
        query: {'page': page, 'page_size': 10, 'ordering': '-fecha'},
      );
}
