import 'package:flutter/material.dart';

abstract final class ClinicColors {
  static const background = Color(0xFFF0FDF4);
  static const surface = Colors.white;
  static const primary = Color(0xFF00796B);
  static const dark = Color(0xFF004D40);
  static const text = Color(0xFF172A26);
  static const muted = Color(0xFF60736E);
  static const border = Color(0xFFDDECE4);
  static const soft = Color(0xFFE8F5EE);
  static const mint = Color(0xFFD7F5EE);
}

abstract final class ClinicTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: ClinicColors.background,
    colorScheme: ColorScheme.fromSeed(
      seedColor: ClinicColors.primary,
      primary: ClinicColors.primary,
      surface: ClinicColors.surface,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: ClinicColors.background,
      foregroundColor: ClinicColors.text,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: ClinicColors.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(18)),
        side: BorderSide(color: ClinicColors.border),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: ClinicColors.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: ClinicColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: ClinicColors.border),
      ),
    ),
  );
}
