import 'package:flutter/material.dart';

import '../../core/session/session_controller.dart';
import '../../core/session/user_profile.dart';
import 'clinic_theme.dart';
import 'data/patient_api.dart';
import 'screens/patient_appointments_screen.dart';
import 'screens/patient_consultations_screen.dart';
import 'screens/patient_dashboard_screen.dart';
import 'screens/patient_history_screen.dart';
import 'screens/patient_information_screen.dart';
import '../shared/notification_bell.dart';

class PatientHomeScreen extends StatefulWidget {
  const PatientHomeScreen({super.key, required this.session});
  final SessionController session;

  @override
  State<PatientHomeScreen> createState() => _PatientHomeScreenState();
}

class _PatientHomeScreenState extends State<PatientHomeScreen> {
  int _index = 0;
  bool _showMyData = false;
  late final PatientApi _api = PatientApi(widget.session.api);

  UserProfile get _profile => widget.session.profile!;

  String get _pageTitle => switch (_index) {
    1 => 'Historia clínica',
    2 => 'Citas médicas',
    3 => 'Consultas médicas',
    _ => 'Portal del paciente',
  };

  @override
  Widget build(BuildContext context) => Theme(
    data: ClinicTheme.light,
    child: Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            _header(),
            Expanded(child: _currentScreen()),
          ],
        ),
      ),
      bottomNavigationBar: _showMyData ? null : _bottomNavigation(),
    ),
  );

  Widget _currentScreen() {
    if (_showMyData) {
      return PatientInformationScreen(
        key: const ValueKey('patient-information'),
        api: _api,
      );
    }
    return switch (_index) {
      1 => PatientHistoryScreen(
        key: const ValueKey('patient-history'),
        api: _api,
      ),
      2 => PatientAppointmentsScreen(
        key: const ValueKey('patient-appointments'),
        api: _api,
        inbox: widget.session.notificationInbox,
      ),
      3 => PatientConsultationsScreen(
        key: const ValueKey('patient-consultations'),
        api: _api,
      ),
      _ => PatientDashboardScreen(
        key: const ValueKey('patient-dashboard'),
        api: _api,
        inbox: widget.session.notificationInbox,
        profile: _profile,
        onOpenHistory: () => _selectTab(1),
        onOpenAppointments: () => _selectTab(2),
        onOpenConsultations: () => _selectTab(3),
      ),
    };
  }

  Widget _header() {
    if (_showMyData) {
      return Padding(
        padding: const EdgeInsets.fromLTRB(12, 5, 18, 10),
        child: Row(
          children: [
            IconButton(
              tooltip: 'Volver al inicio',
              onPressed: () => setState(() => _showMyData = false),
              icon: const Icon(Icons.arrow_back),
            ),
            const _BrandMark(size: 32),
            const SizedBox(width: 9),
            const Expanded(
              child: Text(
                'Mis Datos',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              ),
            ),
            _PatientBadge(),
          ],
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 10, 18, 10),
      child: Column(
        children: [
          Row(
            children: [
              const _BrandMark(size: 38),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _profile.clinicName?.trim().isNotEmpty == true
                          ? _profile.clinicName!
                          : 'Clínica',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: ClinicColors.dark,
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                      ),
                    ),
                    const Text(
                      'PORTAL DEL PACIENTE',
                      style: TextStyle(
                        color: ClinicColors.muted,
                        fontSize: 9,
                        letterSpacing: 0.8,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              NotificationBell(
                inbox: widget.session.notificationInbox,
                color: ClinicColors.text,
                badgeColor: ClinicColors.primary,
              ),
              const SizedBox(width: 2),
              InkWell(
                onTap: _showProfileMenu,
                customBorder: const CircleBorder(),
                child: _Avatar(username: _profile.username),
              ),
            ],
          ),
          if (_index != 0) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                const _PatientBadge(),
                const SizedBox(width: 8),
                Text(
                  _pageTitle,
                  style: const TextStyle(
                    color: ClinicColors.text,
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _bottomNavigation() => SafeArea(
    top: false,
    child: Container(
      margin: const EdgeInsets.fromLTRB(16, 5, 16, 12),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: ClinicColors.border),
        boxShadow: const [
          BoxShadow(
            color: Color(0x12004D40),
            blurRadius: 18,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Row(
        children: [
          _NavItem(
            selected: _index == 0,
            icon: Icons.home_outlined,
            label: 'Inicio',
            onTap: () => _selectTab(0),
          ),
          _NavItem(
            selected: _index == 1,
            icon: Icons.medical_information_outlined,
            label: 'Historia',
            onTap: () => _selectTab(1),
          ),
          _NavItem(
            selected: _index == 2,
            icon: Icons.calendar_month_outlined,
            label: 'Citas',
            onTap: () => _selectTab(2),
          ),
          _NavItem(
            selected: _index == 3,
            icon: Icons.assignment_outlined,
            label: 'Consultas',
            onTap: () => _selectTab(3),
          ),
        ],
      ),
    ),
  );

  void _selectTab(int index) {
    setState(() {
      _showMyData = false;
      _index = index;
    });
  }

  Future<void> _showProfileMenu() async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (sheetContext) => Container(
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 22),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(25)),
        ),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 38,
                height: 4,
                decoration: BoxDecoration(
                  color: ClinicColors.border,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  _Avatar(username: _profile.username, radius: 24),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _profile.username,
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        Text(
                          _profile.email,
                          style: const TextStyle(
                            color: ClinicColors.muted,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const _PatientBadge(),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(height: 1),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const _MenuIcon(icon: Icons.badge_outlined),
                title: const Text('Mis datos personales'),
                subtitle: const Text('Ficha personal y de contacto'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.pop(sheetContext);
                  setState(() => _showMyData = true);
                },
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const _MenuIcon(icon: Icons.settings_outlined),
                title: const Text('Configuración de cuenta'),
                subtitle: Text(
                  '${_profile.username} · ${_profile.roles.join(', ')}',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  Navigator.pop(sheetContext);
                  _showAccountDetails();
                },
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const _MenuIcon(
                  icon: Icons.logout,
                  foreground: Color(0xFFB42318),
                  background: Color(0xFFFFF0EE),
                ),
                title: const Text(
                  'Cerrar sesión',
                  style: TextStyle(color: Color(0xFFB42318)),
                ),
                onTap: () {
                  Navigator.pop(sheetContext);
                  widget.session.logout();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _showAccountDetails() => showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: const Text('Configuración de cuenta'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _accountField('Usuario', _profile.username),
          _accountField('Correo', _profile.email),
          _accountField('Clínica', _profile.clinicName ?? 'Clínica'),
          _accountField('Roles', _profile.roles.join(', ')),
          const SizedBox(height: 8),
          const Text(
            'Para cambiar estos datos, contacta al administrador de tu clínica.',
            style: TextStyle(color: ClinicColors.muted, fontSize: 12),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(dialogContext),
          child: const Text('Cerrar'),
        ),
      ],
    ),
  );
}

Widget _accountField(String label, String value) => Padding(
  padding: const EdgeInsets.only(bottom: 10),
  child: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(color: ClinicColors.muted, fontSize: 12),
      ),
      Text(value.isEmpty ? '—' : value),
    ],
  ),
);

class _BrandMark extends StatelessWidget {
  const _BrandMark({required this.size});
  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      color: ClinicColors.primary,
      borderRadius: BorderRadius.circular(size * 0.28),
    ),
    child: Icon(Icons.add_rounded, color: Colors.white, size: size * 0.72),
  );
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.username, this.radius = 19});
  final String username;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final initials = username.trim().isEmpty
        ? 'P'
        : username.trim().substring(0, 1).toUpperCase();
    return CircleAvatar(
      radius: radius,
      backgroundColor: ClinicColors.mint,
      foregroundColor: ClinicColors.dark,
      child: Text(
        initials,
        style: const TextStyle(fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _PatientBadge extends StatelessWidget {
  const _PatientBadge();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: ClinicColors.mint,
      borderRadius: BorderRadius.circular(20),
    ),
    child: const Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.circle, size: 7, color: ClinicColors.primary),
        SizedBox(width: 5),
        Text(
          'PACIENTE',
          style: TextStyle(
            color: ClinicColors.dark,
            fontSize: 9,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
      ],
    ),
  );
}

class _MenuIcon extends StatelessWidget {
  const _MenuIcon({
    required this.icon,
    this.foreground = ClinicColors.primary,
    this.background = ClinicColors.soft,
  });

  final IconData icon;
  final Color foreground;
  final Color background;

  @override
  Widget build(BuildContext context) => Container(
    width: 38,
    height: 38,
    decoration: BoxDecoration(
      color: background,
      borderRadius: BorderRadius.circular(12),
    ),
    child: Icon(icon, size: 20, color: foreground),
  );
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.selected,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final bool selected;
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Expanded(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 4),
              decoration: BoxDecoration(
                color: selected ? ClinicColors.mint : Colors.transparent,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Icon(
                icon,
                size: 20,
                color: selected ? ClinicColors.primary : ClinicColors.muted,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                color: selected ? ClinicColors.primary : ClinicColors.muted,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
