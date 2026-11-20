import 'dart:async';

import 'package:daily_flutter/daily_flutter.dart';
import 'package:flutter/material.dart';

class TelemedicineCallScreen extends StatefulWidget {
  const TelemedicineCallScreen({
    super.key,
    required this.roomUrl,
    required this.displayName,
    required this.otherParticipantName,
  });

  final String roomUrl;
  final String displayName;
  final String otherParticipantName;

  @override
  State<TelemedicineCallScreen> createState() => _TelemedicineCallScreenState();
}

class _TelemedicineCallScreenState extends State<TelemedicineCallScreen> {
  CallClient? _client;
  StreamSubscription<Event>? _events;
  String? _error;
  bool _joining = true;
  bool _cameraEnabled = true;
  bool _microphoneEnabled = true;
  bool _leaving = false;

  @override
  void initState() {
    super.initState();
    unawaited(_joinCall());
  }

  Future<void> _joinCall() async {
    if (mounted) {
      setState(() {
        _joining = true;
        _error = null;
      });
    }
    CallClient? client;
    try {
      client = await CallClient.create();
      _events = client.events.listen((_) {
        if (mounted) setState(() {});
      });
      await client.setUsername(widget.displayName);
      await client.updateInputs(
        inputs: const InputSettingsUpdate.set(
          camera: CameraInputSettingsUpdate.set(
            isEnabled: BoolUpdate.set(true),
          ),
          microphone: MicrophoneInputSettingsUpdate.set(
            isEnabled: BoolUpdate.set(true),
          ),
        ),
      );
      await client.join(url: Uri.parse(widget.roomUrl));
      if (!mounted) {
        await _disposeClient(client);
        return;
      }
      setState(() {
        _client = client;
        _joining = false;
      });
    } catch (_) {
      if (client != null) await _disposeClient(client);
      if (!mounted) return;
      setState(() {
        _joining = false;
        _error = 'No se pudo conectar a la videollamada. Revisa tu conexión y vuelve a intentarlo.';
      });
    }
  }

  Future<void> _disposeClient(CallClient client) async {
    await _events?.cancel();
    _events = null;
    try {
      await client.leave();
    } catch (_) {}
    await client.dispose();
  }

  Future<void> _toggleCamera() async {
    final client = _client;
    if (client == null) return;
    final next = !_cameraEnabled;
    await client.setInputsEnabled(camera: next);
    if (mounted) setState(() => _cameraEnabled = next);
  }

  Future<void> _toggleMicrophone() async {
    final client = _client;
    if (client == null) return;
    final next = !_microphoneEnabled;
    await client.setInputsEnabled(microphone: next);
    if (mounted) setState(() => _microphoneEnabled = next);
  }

  Future<void> _leaveCall() async {
    if (_leaving) return;
    setState(() => _leaving = true);
    final client = _client;
    _client = null;
    if (client != null) await _disposeClient(client);
    if (mounted) Navigator.of(context).pop();
  }

  @override
  void dispose() {
    final client = _client;
    _client = null;
    if (client != null) unawaited(_disposeClient(client));
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final client = _client;
    return Scaffold(
      backgroundColor: const Color(0xff101817),
      appBar: AppBar(
        backgroundColor: const Color(0xff101817),
        foregroundColor: Colors.white,
        title: const Text('Videollamada'),
        actions: [
          IconButton(
            tooltip: 'Finalizar llamada',
            onPressed: _joining || _leaving ? null : _leaveCall,
            icon: const Icon(Icons.call_end, color: Colors.redAccent),
          ),
        ],
      ),
      body: _joining
          ? const Center(
              child: CircularProgressIndicator(color: Colors.white),
            )
          : _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.videocam_off, color: Colors.white70, size: 48),
                    const SizedBox(height: 16),
                    Text(
                      _error!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(onPressed: _joinCall, child: const Text('Reintentar')),
                  ],
                ),
              ),
            )
          : client == null
          ? const SizedBox.shrink()
          : _buildCall(client),
    );
  }

  Widget _buildCall(CallClient client) {
    final local = client.participants.local;
    final remote = client.participants.remote.values.toList();
    final mainParticipant = remote.isNotEmpty ? remote.first : local;
    final mainLabel = remote.isNotEmpty
        ? widget.otherParticipantName
        : 'Esperando a ${widget.otherParticipantName}';

    return Column(
      children: [
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: _ParticipantVideo(participant: mainParticipant, label: mainLabel),
          ),
        ),
        SizedBox(
          height: 145,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Align(
              alignment: Alignment.centerRight,
              child: SizedBox(
                width: 112,
                child: _ParticipantVideo(
                  participant: local,
                  label: 'Tú',
                  mirror: true,
                ),
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _CallControl(
                icon: _microphoneEnabled ? Icons.mic : Icons.mic_off,
                label: _microphoneEnabled ? 'Silenciar' : 'Activar micrófono',
                onPressed: _toggleMicrophone,
              ),
              const SizedBox(width: 20),
              _CallControl(
                icon: _cameraEnabled ? Icons.videocam : Icons.videocam_off,
                label: _cameraEnabled ? 'Apagar cámara' : 'Encender cámara',
                onPressed: _toggleCamera,
              ),
              const SizedBox(width: 20),
              _CallControl(
                icon: Icons.call_end,
                label: 'Finalizar',
                color: Colors.red,
                onPressed: _leaveCall,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ParticipantVideo extends StatefulWidget {
  const _ParticipantVideo({
    required this.participant,
    required this.label,
    this.mirror = false,
  });

  final Participant participant;
  final String label;
  final bool mirror;

  @override
  State<_ParticipantVideo> createState() => _ParticipantVideoState();
}

class _ParticipantVideoState extends State<_ParticipantVideo> {
  final VideoViewController _controller = VideoViewController();

  @override
  void initState() {
    super.initState();
    _syncTrack();
  }

  @override
  void didUpdateWidget(covariant _ParticipantVideo oldWidget) {
    super.didUpdateWidget(oldWidget);
    _syncTrack();
  }

  Future<void> _syncTrack() =>
      _controller.setTrack(widget.participant.media?.camera.track);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(18),
    child: Stack(
      fit: StackFit.expand,
      children: [
        const ColoredBox(color: Color(0xff25312f)),
        if (!widget.participant.isCameraMuted)
          Transform(
            alignment: Alignment.center,
            transform: Matrix4.diagonal3Values(widget.mirror ? -1 : 1, 1, 1),
            child: VideoView(controller: _controller, fit: VideoViewFit.cover),
          )
        else
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.person, color: Colors.white70, size: 52),
                const SizedBox(height: 8),
                Text(widget.label, style: const TextStyle(color: Colors.white)),
              ],
            ),
          ),
        Positioned(
          left: 10,
          bottom: 10,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Colors.black54,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
              child: Text(
                widget.label,
                style: const TextStyle(color: Colors.white, fontSize: 12),
              ),
            ),
          ),
        ),
      ],
    ),
  );
}

class _CallControl extends StatelessWidget {
  const _CallControl({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.color = const Color(0xff34433f),
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      IconButton.filled(
        onPressed: onPressed,
        style: IconButton.styleFrom(
          backgroundColor: color,
          foregroundColor: Colors.white,
          fixedSize: const Size(58, 58),
        ),
        icon: Icon(icon),
      ),
      const SizedBox(height: 5),
      Text(label, style: const TextStyle(color: Colors.white70, fontSize: 11)),
    ],
  );
}
