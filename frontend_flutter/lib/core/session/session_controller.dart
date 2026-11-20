import 'dart:async';

import 'package:flutter/foundation.dart';

import '../network/api_client.dart';
import '../notifications/notification_inbox.dart';
import '../notifications/push_notification_service.dart';
import 'user_profile.dart';

class SessionController extends ChangeNotifier {
  SessionController(
    this.api, {
    this.pushNotifications,
    NotificationInboxController? notificationInbox,
  }) : notificationInbox =
           notificationInbox ?? NotificationInboxController(api);

  final ApiClient api;
  final PushNotificationService? pushNotifications;
  final NotificationInboxController notificationInbox;
  UserProfile? profile;
  bool isRestoring = true;
  bool isBusy = false;
  String? errorMessage;

  Future<void> restore() async {
    final access = await api.tokenStorage.access;
    if (access != null) {
      try {
        profile = UserProfile.fromJson(await api.getMap('auth/me/'));
        unawaited(pushNotifications?.login(api));
        unawaited(notificationInbox.refresh());
      } catch (_) {
        await api.tokenStorage.clear();
      }
    }
    isRestoring = false;
    notifyListeners();
  }

  Future<bool> login(String username, String password) async {
    isBusy = true;
    errorMessage = null;
    notifyListeners();
    try {
      final data = await api.postMap(
        'auth/login/',
        data: {'username': username.trim(), 'password': password},
        skipAuth: true,
      );
      final access = data['access'];
      final refresh = data['refresh'];
      final user = data['usuario'];
      if (access is! String || refresh is! String || user is! Map) {
        throw const FormatException(
          'El backend devolvió una respuesta de inicio de sesión inválida.',
        );
      }
      await api.tokenStorage.save(access: access, refresh: refresh);
      profile = UserProfile.fromJson(Map<String, dynamic>.from(user));
      unawaited(pushNotifications?.login(api));
      unawaited(notificationInbox.refresh());
      return true;
    } catch (error) {
      errorMessage = apiErrorMessage(error);
      return false;
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    final refresh = await api.tokenStorage.refresh;
    await pushNotifications?.logout();
    try {
      if (refresh != null) {
        await api.postMap('auth/logout/', data: {'refresh': refresh});
      }
    } catch (_) {
      // El cierre local se completa aunque el backend no responda.
    }
    await api.tokenStorage.clear();
    notificationInbox.clear();
    profile = null;
    notifyListeners();
  }
}
