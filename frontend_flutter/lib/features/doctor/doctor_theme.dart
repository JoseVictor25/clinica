import 'package:flutter/material.dart';

abstract final class DoctorColors {
  static const background = Color(0xFFF0FDF4);
  static const surface = Colors.white;
  static const teal = Color(0xFF00796B);
  static const darkTeal = Color(0xFF00574F);
  static const text = Color(0xFF172A26);
  static const muted = Color(0xFF60736E);
  static const border = Color(0xFFDDECE4);
  static const soft = Color(0xFFE8F5EE);
  static const mint = Color(0xFFD7F5EE);
  static const lavender = Color(0xFFE8EAFE);
  static const red = Color(0xFFDC4C4C);
}

abstract final class DoctorTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: DoctorColors.background,
    colorScheme: ColorScheme.fromSeed(
      seedColor: DoctorColors.teal,
      primary: DoctorColors.teal,
      surface: DoctorColors.surface,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: DoctorColors.background,
      foregroundColor: DoctorColors.text,
      elevation: 0,
    ),
    cardTheme: CardThemeData(
      color: DoctorColors.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(17),
        side: const BorderSide(color: DoctorColors.border),
      ),
    ),
  );
}
