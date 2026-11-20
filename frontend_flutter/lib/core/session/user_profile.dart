class UserProfile {
  const UserProfile({
    required this.id,
    required this.username,
    required this.email,
    required this.roles,
    required this.clinicName,
  });

  final int id;
  final String username;
  final String email;
  final List<String> roles;
  final String? clinicName;

  bool get isDoctor => roles.contains('Médico');
  bool get isPatient => roles.contains('Paciente');

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
    id: (json['id'] as num).toInt(),
    username: json['username'] as String? ?? '',
    email: json['email'] as String? ?? '',
    roles: (json['roles'] as List? ?? const []).whereType<String>().toList(),
    clinicName: json['clinica_nombre'] as String?,
  );
}
