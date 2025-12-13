
import 'package:flutter/material.dart';
import 'screens/login_screen.dart';

void main() {
  runApp(const SecureVaultApp());
}

class SecureVaultApp extends StatelessWidget {
  const SecureVaultApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SecureVault',
      theme: ThemeData.dark().copyWith(
        primaryColor: const Color(0xFF6366F1),
        scaffoldBackgroundColor: const Color(0xFF0F172A),
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF6366F1),
          secondary: const Color(0xFFEC4899),
          surface: const Color(0xFF1E293B),
        ),
        useMaterial3: true,
      ),
      home: const LoginScreen(),
    );
  }
}
