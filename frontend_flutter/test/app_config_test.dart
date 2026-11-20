import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/core/config/app_config.dart';

void main() {
  test('normalizes the API base URL with a trailing slash', () {
    final config = AppConfig.fromEnvironment({
      'API_BASE_URL': 'http://127.0.0.1:8000/api/v1',
    });

    expect(config.apiBaseUrl, 'http://127.0.0.1:8000/api/v1/');
  });

  test('uses the Android emulator URL on Android', () {
    final config = AppConfig.fromEnvironment({
      'API_BASE_URL': 'http://127.0.0.1:8000/api/v1/',
      'API_BASE_URL_ANDROID': 'http://10.0.2.2:8000/api/v1/',
    }, android: true);

    expect(config.apiBaseUrl, 'http://10.0.2.2:8000/api/v1/');
  });

  test('requires API_BASE_URL', () {
    expect(() => AppConfig.fromEnvironment({}), throwsStateError);
  });

  test('uses production build overrides before dotenv values', () {
    final config = AppConfig.fromEnvironment(
      {'API_BASE_URL': 'http://127.0.0.1:8000/api/v1/'},
      apiBaseUrlOverride: 'https://clinica.example.com/api/v1',
    );

    expect(config.apiBaseUrl, 'https://clinica.example.com/api/v1/');
  });

  test('uses the Android production override on Android builds', () {
    final config = AppConfig.fromEnvironment(
      {
        'API_BASE_URL': 'http://127.0.0.1:8000/api/v1/',
        'API_BASE_URL_ANDROID': 'http://10.0.2.2:8000/api/v1/',
      },
      android: true,
      apiBaseUrlOverride: 'https://clinica.example.com/api/v1/',
      androidApiBaseUrlOverride:
          'https://clinica.example.com/api/v1/',
    );

    expect(config.apiBaseUrl, 'https://clinica.example.com/api/v1/');
  });
}
