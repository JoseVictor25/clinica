class AppConfig {
  const AppConfig({required this.apiBaseUrl});

  final String apiBaseUrl;

  factory AppConfig.fromEnvironment(
    Map<String, String> environment, {
    bool android = false,
    String apiBaseUrlOverride = const String.fromEnvironment('API_BASE_URL'),
    String androidApiBaseUrlOverride = const String.fromEnvironment(
      'API_BASE_URL_ANDROID',
    ),
  }) {
    final key = android ? 'API_BASE_URL_ANDROID' : 'API_BASE_URL';
    final compileTimeValue = android
        ? androidApiBaseUrlOverride.trim()
        : apiBaseUrlOverride.trim();
    final value = compileTimeValue.isNotEmpty
        ? compileTimeValue
        : environment[key]?.trim();
    if (value == null || value.isEmpty) {
      throw StateError('Define $key en frontend_flutter/.env');
    }
    return AppConfig(apiBaseUrl: value.endsWith('/') ? value : '$value/');
  }
}
