import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../network/api_client.dart';

class PushNotificationService {
  PushNotificationService({
    required this.enabled,
    required this.messengerKey,
    this.onNotificationReceived,
  });

  final bool enabled;
  final GlobalKey<ScaffoldMessengerState> messengerKey;
  final Future<void> Function()? onNotificationReceived;
  FirebaseMessaging? _messaging;
  StreamSubscription<String>? _registrationSubscription;
  StreamSubscription<RemoteMessage>? _foregroundSubscription;
  StreamSubscription<RemoteMessage>? _openedSubscription;
  ApiClient? _api;
  String? _installationId;
  String? _savedInstallationId;
  Completer<String>? _pendingRegistration;
  String? _initializationError;

  Future<void> initialize() async {
    if (!enabled || kIsWeb) return;

    try {
      await Firebase.initializeApp();
      final messaging = FirebaseMessaging.instance;
      _messaging = messaging;
      _registrationSubscription = messaging.onRegistered.listen((
        installationId,
      ) {
        _installationId = installationId;
        final pending = _pendingRegistration;
        if (pending != null && !pending.isCompleted) {
          pending.complete(installationId);
        }
        final api = _api;
        if (api != null) unawaited(_saveInstallation(api, installationId));
      });
      _foregroundSubscription = FirebaseMessaging.onMessage.listen(
        _showMessage,
      );
      _openedSubscription = FirebaseMessaging.onMessageOpenedApp.listen(
        _showMessage,
      );
      final initialMessage = await messaging.getInitialMessage();
      if (initialMessage != null) _showMessage(initialMessage);
    } catch (error) {
      _initializationError = error.toString();
      debugPrint('Firebase Messaging no pudo inicializarse: $error');
    }
  }

  Future<void> login(ApiClient api) async {
    final messaging = _messaging;
    if (messaging == null) {
      _showStatus(
        _initializationError == null
            ? 'Las notificaciones push no están habilitadas en esta compilación.'
            : 'No se pudo iniciar Firebase. Revisa la configuración de Android y vuelve a abrir la app.',
      );
      return;
    }
    try {
      final settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      if (settings.authorizationStatus != AuthorizationStatus.authorized &&
          settings.authorizationStatus != AuthorizationStatus.provisional) {
        _showStatus(
          'Permite las notificaciones de Clínica en los ajustes de Android para recibir avisos.',
        );
        return;
      }
      if (defaultTargetPlatform == TargetPlatform.iOS) {
        var apnsToken = await messaging.getAPNSToken();
        for (var attempt = 0; apnsToken == null && attempt < 10; attempt++) {
          await Future<void>.delayed(const Duration(milliseconds: 500));
          apnsToken = await messaging.getAPNSToken();
        }
        if (apnsToken == null) {
          debugPrint('Firebase Messaging espera el token APNs de iOS.');
          return;
        }
      }
      _api = api;

      if (_installationId != null) {
        await _saveInstallation(api, _installationId!);
        return;
      }

      final pending = Completer<String>();
      _pendingRegistration = pending;
      await messaging.register();
      final installationId =
          _installationId ??
          await pending.future.timeout(const Duration(seconds: 20));
      await _saveInstallation(api, installationId);
    } catch (error) {
      debugPrint('No se pudo registrar el dispositivo en Firebase: $error');
      final codigoError = error is FirebaseException
          ? error.code
          : error.runtimeType.toString();
      _showStatus(
        'Falló el registro push ($codigoError). Revisa Firebase/Google Play Services y vuelve a intentarlo.',
      );
    } finally {
      _pendingRegistration = null;
    }
  }

  Future<void> logout() async {
    final api = _api;
    final installationId = _installationId;
    if (api != null && installationId != null) {
      try {
        await api.deleteMap(
          'notificaciones/dispositivos/',
          data: {'token': installationId, 'plataforma': _platform},
        );
      } catch (_) {
        // Se completa el cierre local aunque el servidor no responda.
      }
    }
    _api = null;
    _savedInstallationId = null;
    try {
      await _messaging?.unregister();
    } catch (_) {
      // El dispositivo puede volver a registrarse en el siguiente inicio.
    }
    _installationId = null;
  }

  String get _platform => switch (defaultTargetPlatform) {
    TargetPlatform.iOS => 'IOS',
    _ => 'ANDROID',
  };

  Future<void> _saveInstallation(ApiClient api, String installationId) async {
    if (_savedInstallationId == installationId) return;
    try {
      await api.postMap(
        'notificaciones/dispositivos/',
        data: {'token': installationId, 'plataforma': _platform},
      );
      _savedInstallationId = installationId;
      _showStatus(
        'Este teléfono quedó registrado para recibir notificaciones.',
      );
    } catch (error) {
      debugPrint(
        'No se pudo registrar el dispositivo para notificaciones: $error',
      );
      _showStatus(
        'Firebase está activo, pero el servidor no pudo registrar este teléfono. Vuelve a iniciar sesión.',
      );
    }
  }

  void _showStatus(String message) {
    final messenger = messengerKey.currentState;
    if (messenger == null) return;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  void _showMessage(RemoteMessage message) {
    if (onNotificationReceived != null) {
      unawaited(onNotificationReceived!());
    }
    final notification = message.notification;
    final messenger = messengerKey.currentState;
    if (notification == null || messenger == null) return;
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            '${notification.title ?? 'Clínica'}: ${notification.body ?? 'Tienes una actualización.'}',
          ),
          duration: const Duration(seconds: 5),
        ),
      );
  }

  Future<void> dispose() async {
    await _registrationSubscription?.cancel();
    await _foregroundSubscription?.cancel();
    await _openedSubscription?.cancel();
  }
}
