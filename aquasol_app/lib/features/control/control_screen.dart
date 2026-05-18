import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import './scheduling_screen.dart';

class ControlScreen extends StatefulWidget {
  const ControlScreen({super.key});

  @override
  State<ControlScreen> createState() => _ControlScreenState();
}

class _ControlScreenState extends State<ControlScreen> {
  final _apiService = ApiService();
  bool _isAutoMode = true;
  List<dynamic> _zones = [];
  bool _isLoading = true;
  String? _selectedZoneId;
  Map<String, dynamic>? _waterUsage;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final data = await _apiService.getZones();
      _waterUsage = await _apiService.getWaterUsage();
      if (mounted) {
        setState(() {
          _zones = data;
          if (_zones.isNotEmpty) {
            _selectedZoneId ??= _zones[0]['zone_id'].toString();
          }
        });
      }
    } catch (e) {
      debugPrint('Control load error: $e');
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildModeToggle(),
                            if (!_isAutoMode) _buildManualAlert(),
                            const SizedBox(height: 24),
                            _buildWaterBudgetCard(),
                            const SizedBox(height: 32),
                            Text(
                              'ZONES',
                              style: AppTextStyles.caption.copyWith(
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.2,
                                color: AppColors.textMuted,
                              ),
                            ),
                            const SizedBox(height: 16),
                            ..._zones.map((z) => _buildZoneCard(z)),
                            const SizedBox(height: 40),
                          ],
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text('Control Center', style: AppTextStyles.screenTitle),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: const Icon(LucideIcons.settings, size: 20, color: AppColors.textPrimary),
          ),
        ],
      ),
    );
  }

  Widget _buildModeToggle() {
    return Container(
      height: 56,
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildToggleButton(
              label: 'AI Mode',
              icon: LucideIcons.wand2,
              isSelected: _isAutoMode,
              onTap: () => setState(() => _isAutoMode = true),
            ),
          ),
          Expanded(
            child: _buildToggleButton(
              label: 'Manual',
              icon: LucideIcons.sliders,
              isSelected: !_isAutoMode,
              onTap: () => setState(() => _isAutoMode = false),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToggleButton({
    required String label,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.accentGreen : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          boxShadow: isSelected
              ? [BoxShadow(color: AppColors.accentGreen.withValues(alpha: 0.3), blurRadius: 8, offset: const Offset(0, 4))]
              : null,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 18,
              color: isSelected ? Colors.white : AppColors.textMuted,
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: AppTextStyles.label.copyWith(
                color: isSelected ? Colors.white : AppColors.textMuted,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildManualAlert() {
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFED7AA)),
      ),
      child: Row(
        children: [
          const Icon(LucideIcons.alertTriangle, size: 18, color: Color(0xFFEA580C)),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Manual mode active — AI suggestions paused.',
              style: AppTextStyles.bodySmall.copyWith(color: const Color(0xFF9A3412)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWaterBudgetCard() {
    final waterUsedLiters = _waterUsage?['water_used_liters'] ?? 0;
    const budgetLiters = 28000.0;
    final progress = (waterUsedLiters / budgetLiters).clamp(0.0, 1.0);

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0EA5E9), Color(0xFF2563EB)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF2563EB).withValues(alpha: 0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Water Budget',
            style: AppTextStyles.label.copyWith(color: Colors.white70),
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              SizedBox(
                width: 120,
                height: 120,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    CircularProgressIndicator(
                      value: progress,
                      strokeWidth: 12,
                      backgroundColor: Colors.white.withValues(alpha: 0.2),
                      valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                      strokeCap: StrokeCap.round,
                    ),
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${(waterUsedLiters / 1000).toStringAsFixed(1)}',
                          style: AppTextStyles.dataValue.copyWith(color: Colors.white, fontSize: 24),
                        ),
                        Text(
                          'kL used',
                          style: AppTextStyles.bodySmall.copyWith(color: Colors.white70, fontSize: 10),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildBudgetItem('Used today', '$waterUsedLiters L'),
                    const SizedBox(height: 16),
                    _buildBudgetItem('Remaining', '${(budgetLiters - waterUsedLiters).toInt()} L'),
                    const SizedBox(height: 16),
                    _buildBudgetItem('Budget', '${budgetLiters.toInt()} L', isBold: true),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBudgetItem(String label, String value, {bool isBold = false}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: AppTextStyles.bodySmall.copyWith(color: Colors.white70)),
        Text(
          value,
          style: AppTextStyles.label.copyWith(
            color: Colors.white,
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
            fontSize: isBold ? 18 : 16,
          ),
        ),
      ],
    );
  }

  Widget _buildZoneCard(Map<String, dynamic> zone) {
    final moisture = zone['current_moisture'] ?? 0;
    final name = zone['name'] ?? 'Zone';
    final crop = zone['crop_type'] ?? 'Unknown';
    final waterUsed = zone['water_used_today'] ?? '5,058';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: AppTextStyles.label.copyWith(fontSize: 18, fontWeight: FontWeight.bold)),
                  Text('$crop · $waterUsed L today', style: AppTextStyles.bodySmall.copyWith(color: AppColors.textMuted)),
                ],
              ),
              Text(
                '$moisture%',
                style: AppTextStyles.label.copyWith(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: moisture / 100,
              backgroundColor: const Color(0xFFF1F5F9),
              color: AppColors.accentBlue,
              minHeight: 6,
            ),
          ),
          const SizedBox(height: 20),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: _isAutoMode
                    ? _buildActionButton(
                        label: 'AI Auto',
                        icon: LucideIcons.wand2,
                        color: const Color(0xFF8B5CF6),
                        onTap: () {},
                      )
                    : _buildActionButton(
                        label: 'Irrigate Now',
                        icon: LucideIcons.droplets,
                        color: AppColors.accentGreen,
                        onTap: () => _handleManualIrrigate(zone['zone_id']),
                      ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _buildActionButton(
                  label: 'Schedule',
                  icon: LucideIcons.calendar,
                  color: Colors.white,
                  textColor: AppColors.textPrimary,
                  borderColor: AppColors.border,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const SchedulingScreen()),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required String label,
    required IconData icon,
    required Color color,
    Color? textColor,
    Color? borderColor,
    required VoidCallback onTap,
  }) {
    final isWhite = color == Colors.white;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 48,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(12),
          border: borderColor != null ? Border.all(color: borderColor) : null,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 16, color: isWhite ? AppColors.textPrimary : Colors.white),
            const SizedBox(width: 8),
            Text(
              label,
              style: AppTextStyles.label.copyWith(
                color: textColor ?? Colors.white,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleManualIrrigate(dynamic zoneId) async {
    final res = await _apiService.manualOverride(
      zoneId: zoneId.toString(),
      action: 'irrigate',
      durationMin: 15,
      reason: 'Manual override from Control Center',
    );
    if (mounted) {
      if (res != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Irrigation started for Zone $zoneId')),
        );
        _load(); // Refresh state
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to start irrigation.')),
        );
      }
    }
  }
}
