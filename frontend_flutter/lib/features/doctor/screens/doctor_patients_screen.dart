import 'package:flutter/material.dart';

import '../../../core/models/page_result.dart';
import '../../../core/network/api_client.dart';
import '../../../core/notifications/notification_inbox.dart';
import '../data/doctor_api.dart';
import '../doctor_theme.dart';
import 'doctor_patient_history_screen.dart';

class DoctorPatientsScreen extends StatefulWidget {
  const DoctorPatientsScreen({
    super.key,
    required this.api,
    required this.inbox,
  });
  final DoctorApi api;
  final NotificationInboxController inbox;

  @override
  State<DoctorPatientsScreen> createState() => _DoctorPatientsScreenState();
}

class _DoctorPatientsScreenState extends State<DoctorPatientsScreen> {
  final _searchController = TextEditingController();
  String _search = '';
  late Future<PageResult> _future;
  late int _lastInboxRefresh;

  @override
  void initState() {
    super.initState();
    _future = widget.api.patients();
    _lastInboxRefresh = widget.inbox.refreshVersion;
    widget.inbox.addListener(_onInboxChanged);
  }

  void _onInboxChanged() {
    if (!mounted || _lastInboxRefresh == widget.inbox.refreshVersion) return;
    _lastInboxRefresh = widget.inbox.refreshVersion;
    _reload();
  }

  @override
  void dispose() {
    widget.inbox.removeListener(_onInboxChanged);
    _searchController.dispose();
    super.dispose();
  }

  void _performSearch() {
    final query = _searchController.text.trim();
    final future = widget.api.patients(search: query);
    setState(() {
      _search = query;
      _future = future;
    });
  }

  void _reload() {
    final future = widget.api.patients(search: _search);
    setState(() => _future = future);
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(17, 8, 17, 13),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Pacientes',
              style: TextStyle(
                fontSize: 25,
                fontWeight: FontWeight.w800,
                color: DoctorColors.text,
              ),
            ),
            const SizedBox(height: 3),
            const Text(
              'Consulta los expedientes de tu clínica.',
              style: TextStyle(color: DoctorColors.muted, fontSize: 12),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _performSearch(),
              decoration: InputDecoration(
                hintText: 'Buscar por C.I., nombre o teléfono...',
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: IconButton(
                  tooltip: 'Buscar',
                  onPressed: _performSearch,
                  icon: const Icon(Icons.tune_rounded),
                ),
                filled: true,
                fillColor: Colors.white,
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(15),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ],
        ),
      ),
      Expanded(
        child: FutureBuilder<PageResult>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return _ErrorState(error: snapshot.error!, onRetry: _reload);
            }
            final result = snapshot.data!;
            if (result.results.isEmpty) {
              return RefreshIndicator(
                onRefresh: () async {
                  final future = widget.api.patients(search: _search);
                  setState(() => _future = future);
                  try {
                    await future;
                  } catch (_) {}
                },
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  children: [
                    const SizedBox(height: 150),
                    const Icon(
                      Icons.person_search_outlined,
                      size: 42,
                      color: DoctorColors.teal,
                    ),
                    const SizedBox(height: 12),
                    Center(
                      child: Text(
                        _search.isEmpty
                            ? 'No hay pacientes registrados.'
                            : 'No se encontraron pacientes.',
                        style: const TextStyle(color: DoctorColors.muted),
                      ),
                    ),
                  ],
                ),
              );
            }
            return RefreshIndicator(
              onRefresh: () async {
                final future = widget.api.patients(search: _search);
                setState(() => _future = future);
                try {
                  await future;
                } catch (_) {}
              },
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(15, 0, 15, 20),
                itemCount: result.results.length,
                separatorBuilder: (context, index) => const SizedBox(height: 8),
                itemBuilder: (context, index) => _PatientCard(
                  patient: result.results[index],
                  onHistory: _openHistory,
                ),
              ),
            );
          },
        ),
      ),
    ],
  );

  void _openHistory(int id, String name) => Navigator.of(context).push<void>(
    MaterialPageRoute(
      builder: (_) => DoctorPatientHistoryScreen(
        api: widget.api,
        patientId: id,
        patientName: name,
      ),
    ),
  );
}

class _PatientCard extends StatelessWidget {
  const _PatientCard({required this.patient, required this.onHistory});
  final Map<String, dynamic> patient;
  final void Function(int, String) onHistory;

  @override
  Widget build(BuildContext context) {
    final first = patient['nombre']?.toString() ?? '';
    final last = patient['apellido']?.toString() ?? '';
    final name = '$first $last'.trim();
    final initials = [first, last]
        .where((value) => value.isNotEmpty)
        .map((value) => value[0].toUpperCase())
        .take(2)
        .join();
    final id = (patient['id'] as num?)?.toInt();

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        child: Row(
          children: [
            CircleAvatar(
              radius: 21,
              backgroundColor: _avatarColor(initials),
              foregroundColor: DoctorColors.teal,
              child: Text(
                initials.isEmpty ? '?' : initials,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 12,
                ),
              ),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    name.isEmpty ? 'Paciente' : name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    'C.I. ${patient['ci'] ?? '—'} · Tel. ${patient['telefono'] ?? '—'}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: DoctorColors.muted,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
            TextButton.icon(
              onPressed: id == null ? null : () => onHistory(id, name),
              icon: const Icon(Icons.medical_information_outlined, size: 16),
              label: const Text('Historia'),
              style: TextButton.styleFrom(
                backgroundColor: DoctorColors.soft,
                foregroundColor: DoctorColors.teal,
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 8),
                textStyle: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 10,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Color _avatarColor(String initials) =>
      initials.hashCode.isEven ? DoctorColors.soft : DoctorColors.mint;
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});
  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.cloud_off_outlined,
            size: 38,
            color: DoctorColors.muted,
          ),
          const SizedBox(height: 10),
          Text(apiErrorMessage(error), textAlign: TextAlign.center),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Reintentar')),
        ],
      ),
    ),
  );
}
