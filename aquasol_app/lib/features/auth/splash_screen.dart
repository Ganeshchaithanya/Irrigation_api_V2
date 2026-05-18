import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  late ApiService _apiService;

  @override
  void initState() {
    super.initState();
    _apiService = Provider.of<ApiService>(context, listen: false);
    _checkAuthState();
  }

  Future<void> _checkAuthState() async {
    await Future.delayed(const Duration(milliseconds: 2000));
    if (!mounted) return;

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('access_token');
    final onboardingDone = prefs.getBool('onboarding_done') ?? false;

    // No token — first visit or logged out
    if (token == null) {
      if (!onboardingDone) {
        if (mounted) context.go('/get-started');
      } else {
        if (mounted) context.go('/login');
      }
      return;
    }

    // Has token — validate and check for farm
    try {
      final profile = await _apiService.getMe();

      if (profile == null) {
        await prefs.remove('access_token');
        if (mounted) context.go('/login');
        return;
      }

      final zones = await _apiService.getZones();
      if (mounted) {
        if (zones.isNotEmpty) {
          context.go('/home');
        } else {
          context.go('/farm-setup');
        }
      }
    } catch (e) {
      // Token is invalid (deleted user, expired, etc.) — clear it and go to login
      await prefs.remove('access_token');
      if (mounted) context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        children: [
          // Center content: Logo and subtitle
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Image.asset(
                  'assets/images/logo.png',
                  width: 250,
                  fit: BoxFit.contain,
                ),
                const SizedBox(height: 32),
                Text(
                  'Intelligence in every drop.',
                  style: AppTextStyles.bodyMedium.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
          
          // Bottom loading indicator
          Positioned(
            left: 48,
            right: 48,
            bottom: 64,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: const LinearProgressIndicator(
                    backgroundColor: AppColors.primaryLight,
                    valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
                    minHeight: 4,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Loading your farm data...',
                  style: AppTextStyles.caption.copyWith(
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
