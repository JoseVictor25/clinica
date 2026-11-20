import 'package:flutter/material.dart';

import 'core/session/session_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/doctor/doctor_home_screen.dart';
import 'features/patient/patient_home_screen.dart';

class ClinicaApp extends StatelessWidget {
  const ClinicaApp({
    super.key,
    required this.session,
    required this.messengerKey,
  });

  final SessionController session;
  final GlobalKey<ScaffoldMessengerState> messengerKey;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      scaffoldMessengerKey: messengerKey,
      title: 'Clínica',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff087e8b)),
        useMaterial3: true,
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
        ),
      ),
      home: AnimatedBuilder(
        animation: session,
        builder: (context, _) {
          if (session.isRestoring) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          final profile = session.profile;
          if (profile == null) return LoginScreen(session: session);
          if (profile.isDoctor) {
            return DoctorHomeScreen(session: session);
          }
          if (profile.isPatient) {
            return PatientHomeScreen(session: session);
          }
          return Scaffold(
            appBar: AppBar(title: const Text('Clínica')),
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.lock_outline, size: 48),
                    const SizedBox(height: 12),
                    const Text(
                      'Esta app móvil está habilitada para médicos y pacientes.',
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: session.logout,
                      child: const Text('Cerrar sesión'),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
