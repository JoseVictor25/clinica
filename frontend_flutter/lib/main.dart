import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'app.dart';
import 'core/config/app_config.dart';
import 'core/network/api_client.dart';
import 'core/notifications/notification_inbox.dart';
import 'core/notifications/push_notification_service.dart';
import 'core/session/session_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  final messengerKey = GlobalKey<ScaffoldMessengerState>();
  final config = AppConfig.fromEnvironment(
    dotenv.env,
    android: !kIsWeb && defaultTargetPlatform == TargetPlatform.android,
  );
  final api = ApiClient(config.apiBaseUrl);
  final notificationInbox = NotificationInboxController(api);
  final pushNotifications = PushNotificationService(
    enabled: dotenv.env['FIREBASE_ENABLED']?.toLowerCase() == 'true',
    messengerKey: messengerKey,
    onNotificationReceived: notificationInbox.refresh,
  );
  try {
    await pushNotifications.initialize();
  } catch (error) {
    debugPrint('Firebase Messaging no pudo inicializarse: $error');
  }
  final session = SessionController(
    api,
    pushNotifications: pushNotifications,
    notificationInbox: notificationInbox,
  );
  runApp(ClinicaApp(session: session, messengerKey: messengerKey));
  await session.restore();
}
