import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/core/network/api_client.dart';

void main() {
  test('explains when a patient account is not linked to a record', () {
    final error = DioException(
      requestOptions: RequestOptions(path: '/portal-paciente/mi-informacion/'),
      response: Response<dynamic>(
        requestOptions: RequestOptions(
          path: '/portal-paciente/mi-informacion/',
        ),
        statusCode: 409,
        data: {
          'codigo': 'paciente_no_vinculado',
          'mensaje': 'El usuario no está vinculado a un paciente.',
        },
      ),
    );

    expect(apiErrorCode(error), 'paciente_no_vinculado');
    expect(apiErrorMessage(error), contains('rol Paciente'));
    expect(apiErrorMessage(error), contains('expediente'));
    expect(apiErrorMessage(error), isNot(contains('DioException')));
  });
}
