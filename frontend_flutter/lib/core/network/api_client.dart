import 'package:dio/dio.dart';

import '../storage/token_storage.dart';

class ApiClient {
  ApiClient(String baseUrl, {TokenStorage? tokenStorage})
    : tokenStorage = tokenStorage ?? TokenStorage() {
    dio = Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 25),
        headers: const {'Content-Type': 'application/json'},
      ),
    );
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          if (options.extra['skipAuth'] != true) {
            final access = await this.tokenStorage.access;
            if (access != null) {
              options.headers['Authorization'] = 'Bearer $access';
            }
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          final request = error.requestOptions;
          if (error.response?.statusCode != 401 ||
              request.extra['skipAuth'] == true ||
              request.extra['retried'] == true ||
              request.path.endsWith('auth/refresh/')) {
            handler.next(error);
            return;
          }
          try {
            final access = await _renewAccess();
            request
              ..extra['retried'] = true
              ..headers['Authorization'] = 'Bearer $access';
            handler.resolve(await dio.fetch<dynamic>(request));
          } catch (_) {
            await this.tokenStorage.clear();
            handler.next(error);
          }
        },
      ),
    );
  }

  late final Dio dio;
  final TokenStorage tokenStorage;
  Future<String>? _renewing;

  Future<String> _renewAccess() {
    return _renewing ??= _requestNewAccess().whenComplete(
      () => _renewing = null,
    );
  }

  Future<String> _requestNewAccess() async {
    final refresh = await tokenStorage.refresh;
    if (refresh == null || refresh.isEmpty) {
      throw StateError('La sesión expiró.');
    }
    final response = await Dio(
      BaseOptions(baseUrl: dio.options.baseUrl),
    ).post<Map<String, dynamic>>('auth/refresh/', data: {'refresh': refresh});
    final data = response.data ?? const <String, dynamic>{};
    final access = data['access'];
    final rotatedRefresh = data['refresh'];
    if (access is! String || access.isEmpty) {
      throw StateError('No se pudo renovar la sesión.');
    }
    await tokenStorage.save(
      access: access,
      refresh: rotatedRefresh is String && rotatedRefresh.isNotEmpty
          ? rotatedRefresh
          : refresh,
    );
    return access;
  }

  Future<Map<String, dynamic>> getMap(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    final response = await dio.get<dynamic>(path, queryParameters: query);
    return _asMap(response.data);
  }

  Future<Map<String, dynamic>> postMap(
    String path, {
    Object? data,
    bool skipAuth = false,
  }) async {
    final response = await dio.post<dynamic>(
      path,
      data: data,
      options: Options(extra: {'skipAuth': skipAuth}),
    );
    if (response.data == null) return <String, dynamic>{};
    return _asMap(response.data);
  }

  Future<Map<String, dynamic>> deleteMap(String path, {Object? data}) async {
    final response = await dio.delete<dynamic>(path, data: data);
    if (response.data == null) return <String, dynamic>{};
    return _asMap(response.data);
  }

  Future<List<Map<String, dynamic>>> getList(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    final response = await dio.get<dynamic>(path, queryParameters: query);
    final data = response.data;
    final rows = data is List
        ? data
        : data is Map
        ? data['results']
        : null;
    if (rows is! List) return <Map<String, dynamic>>[];
    return rows.whereType<Map>().map(_asMap).toList();
  }

  static Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) {
      return value.map((key, value) => MapEntry(key.toString(), value));
    }
    throw const FormatException(
      'El servidor devolvió una respuesta inesperada.',
    );
  }
}

String apiErrorMessage(Object error) {
  if (error is DioException) {
    final data = error.response?.data;
    if (data is Map) {
      switch (data['codigo']) {
        case 'paciente_no_vinculado':
          return 'Tu cuenta tiene el rol Paciente, pero todavía no está vinculada a un expediente. Pide al administrador de la clínica que vincule tu usuario desde la sección Pacientes.';
        case 'paciente_inactivo':
          return 'El expediente asociado a tu cuenta está inactivo. Contacta al administrador de la clínica.';
        case 'historia_no_disponible':
          return 'Tu expediente todavía no tiene una historia clínica disponible. Contacta a la clínica para que revise tu registro.';
      }
      final message = data['mensaje'] ?? data['detail'];
      if (message is String && message.isNotEmpty) return message;
      final details = data['detalles'] ?? data;
      if (details is Map) {
        for (final value in details.values) {
          if (value is List && value.isNotEmpty) return value.first.toString();
          if (value is String && value.isNotEmpty) return value;
        }
      }
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return 'No se pudo conectar con el servidor. Revisa API_BASE_URL y que Django esté iniciado.';
    }
  }
  return error.toString().replaceFirst('Exception: ', '');
}

String? apiErrorCode(Object error) {
  if (error is! DioException) return null;
  final data = error.response?.data;
  return data is Map ? data['codigo']?.toString() : null;
}
