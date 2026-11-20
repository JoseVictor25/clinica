import '../../../core/network/api_client.dart';
import '../../../core/models/page_result.dart';

class PatientApi {
  PatientApi(this.client);
  final ApiClient client;

  Future<Map<String, dynamic>> myInformation() =>
      client.getMap('portal-paciente/mi-informacion/');
  Future<Map<String, dynamic>> myHistory() =>
      client.getMap('portal-paciente/mi-historia/');

  Future<PageResult> appointments({int page = 1, String? state}) async {
    final data = await client.getMap(
      'portal-paciente/mis-citas/',
      query: {
        'page': page,
        'page_size': 10,
        if (state != null && state.isNotEmpty) 'estado': state,
        'ordering': '-fecha',
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

  Future<PageResult> consultations({int page = 1}) async {
    final data = await client.getMap(
      'portal-paciente/mis-consultas/',
      query: {'page': page, 'page_size': 10, 'ordering': '-fecha'},
    );
    return PageResult(
      count: (data['count'] as num? ?? 0).toInt(),
      results: (data['results'] as List? ?? const [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList(),
    );
  }

  Future<Map<String, dynamic>> prescription(int id) =>
      client.getMap('portal-paciente/mis-recetas/$id/');
}
