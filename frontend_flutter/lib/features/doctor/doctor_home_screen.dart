import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/session/session_controller.dart';
import 'data/doctor_api.dart';
import 'doctor_theme.dart';
import 'screens/doctor_agenda_screen.dart';
import 'screens/doctor_dashboard_screen.dart';
import 'screens/doctor_patients_screen.dart';
import 'screens/doctor_schedules_screen.dart';
import '../shared/notification_bell.dart';

class DoctorHomeScreen extends StatefulWidget {
  const DoctorHomeScreen({super.key, required this.session});
  final SessionController session;

  @override
  State<DoctorHomeScreen> createState() => _DoctorHomeScreenState();
}

class _DoctorHomeScreenState extends State<DoctorHomeScreen> {
  int _index = 0;
  late final DoctorApi _api = DoctorApi(widget.session.api);

  @override
  Widget build(BuildContext context) => Theme(
    data: DoctorTheme.light,
    child: Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            _header(),
            Expanded(
              child: IndexedStack(
                index: _index,
                children: [
                  DoctorDashboardScreen(
                    key: const ValueKey('doctor-dashboard'),
                    api: _api,
                    inbox: widget.session.notificationInbox,
                    username: widget.session.profile?.username ?? 'Médico',
                    onOpenAgenda: () => _selectTab(1),
                    onOpenPatients: () => _selectTab(2),
                  ),
                  DoctorAgendaScreen(
                    key: const ValueKey('doctor-agenda'),
                    api: _api,
                    session: widget.session,
                  ),
                  DoctorPatientsScreen(
                    key: const ValueKey('doctor-patients'),
                    api: _api,
                    inbox: widget.session.notificationInbox,
                  ),
                  DoctorSchedulesScreen(
                    key: const ValueKey('doctor-schedules'),
                    api: _api,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _bottomNavigation(),
    ),
  );

  Widget _header() {
    final profile = widget.session.profile!;
    final label = profile.clinicName?.trim().isNotEmpty == true
        ? profile.clinicName!.toUpperCase()
        : 'CLÍNICA';
    return Padding(
      padding: const EdgeInsets.fromLTRB(17, 10, 15, 10),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: DoctorColors.teal,
              borderRadius: BorderRadius.circular(11),
            ),
            child: const Icon(
              Icons.local_hospital_rounded,
              color: Colors.white,
              size: 21,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: DoctorColors.teal,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: .5,
                  ),
                ),
                Text(
                  '${profile.username} · Médico',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: DoctorColors.text,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          NotificationBell(
            inbox: widget.session.notificationInbox,
            color: DoctorColors.text,
            badgeColor: DoctorColors.red,
          ),
          PopupMenuButton<String>(
            tooltip: 'Cuenta',
            onSelected: (value) {
              if (value == 'logout') widget.session.logout();
            },
            itemBuilder: (context) => [
              PopupMenuItem<String>(
                enabled: false,
                child: SizedBox(
                  width: 190,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        profile.username,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                      Text(profile.email, style: const TextStyle(fontSize: 12)),
                    ],
                  ),
                ),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: 'logout',
                child: Text('Cerrar sesión'),
              ),
            ],
            child: CircleAvatar(
              radius: 18,
              backgroundColor: DoctorColors.darkTeal,
              child: Text(
                profile.username.isEmpty
                    ? 'M'
                    : profile.username.substring(0, 1).toUpperCase(),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bottomNavigation() => SafeArea(
    top: false,
    child: Container(
      margin: const EdgeInsets.fromLTRB(12, 4, 12, 10),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: DoctorColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x10004D40),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          _navItem(0, Icons.grid_view_rounded, 'Inicio'),
          _navItem(1, Icons.calendar_month_outlined, 'Agenda'),
          _navItem(2, Icons.people_alt_outlined, 'Pacientes'),
          _navItem(3, Icons.schedule_outlined, 'Horarios'),
        ],
      ),
    ),
  );

  Widget _navItem(int index, IconData icon, String label) => Expanded(
    child: InkWell(
      onTap: () => _selectTab(index),
      borderRadius: BorderRadius.circular(18),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              color: _index == index ? DoctorColors.teal : DoctorColors.muted,
              size: 21,
            ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                color: _index == index ? DoctorColors.teal : DoctorColors.muted,
                fontSize: 10,
                fontWeight: _index == index ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    ),
  );

  void _selectTab(int index) {
    setState(() => _index = index);
    if (index == 2) {
      unawaited(widget.session.notificationInbox.refresh());
    }
  }
}
