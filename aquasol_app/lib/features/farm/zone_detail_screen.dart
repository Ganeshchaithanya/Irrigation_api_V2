import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/services/api_service.dart';

class ZoneDetailScreen extends StatefulWidget {
  final String zoneId;
  const ZoneDetailScreen({super.key, required this.zoneId});

  @override
  State<ZoneDetailScreen> createState() => _ZoneDetailScreenState();
}

class _ZoneDetailScreenState extends State<ZoneDetailScreen> {
  final _apiService = ApiService();
  bool _isLoading = true;
  Map<String, dynamic>? _zone;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _handleManualIrrigate(String action, {dynamic nodeSlotId}) async {
    await _apiService.manualOverride(
      zoneId: widget.zoneId,
      nodeSlotId: nodeSlotId?.toString(),
      action: action,
      durationMin: 15,
      reason: nodeSlotId != null ? 'Manual override for specific node' : 'Manual override for entire zone',
    );
  }

  Future<void> _load() async {
    final data = await _apiService.getZone(widget.zoneId);
    if (mounted) {
      setState(() {
        _zone = data;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        title: Text(_zone?['name'] ?? 'Zone Details', style: AppTextStyles.screenTitle),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20),
        child: Column(
          children: [
            const SizedBox(height: 20),
            _buildStressGauge(),
            const SizedBox(height: 32),
            _buildSensorGrid(),
            const SizedBox(height: 32),
            _buildActionGrid(),
            const SizedBox(height: 32),
            _buildNodeList(),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildStressGauge() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.white, AppColors.primaryLight.withValues(alpha: 0.5)],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ),
        borderRadius: BorderRadius.circular(32),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.1)),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.05),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        children: [
          Text('PLANT STRESS SCORE', style: AppTextStyles.caption.copyWith(letterSpacing: 1.2, fontWeight: FontWeight.bold)),
          const SizedBox(height: 24),
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 160,
                height: 160,
                child: CircularProgressIndicator(
                  value: (_zone?['health_score'] ?? 85) / 100,
                  strokeWidth: 14,
                  backgroundColor: AppColors.primaryLight,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    (_zone?['health_score'] ?? 85) < 50 ? AppColors.accentRed : AppColors.primary
                  ),
                  strokeCap: StrokeCap.round,
                ),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('${_zone?['health_score'] ?? '--'}', style: AppTextStyles.dataDisplay.copyWith(fontSize: 48, color: AppColors.primary)),
                  Text((_zone?['health_score'] ?? 85) < 50 ? 'CRITICAL' : 'OPTIMAL', style: AppTextStyles.caption.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text('OPTIMAL GROWTH CONDITION', style: AppTextStyles.label.copyWith(color: AppColors.primary, fontSize: 11, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _buildSensorGrid() {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      childAspectRatio: 1.4,
      children: [
        _buildSensorTile('MOISTURE', _zone?['current_moisture'] != null ? '${_zone!['current_moisture']}%' : '--%', LucideIcons.droplet, AppColors.accentBlue),
        _buildSensorTile('TEMP', _zone?['temperature_avg_6h'] != null ? '${_zone!['temperature_avg_6h']}°C' : '--°C', LucideIcons.thermometer, AppColors.accentOrange),
        _buildSensorTile('HUMIDITY', _zone?['humidity_avg_6h'] != null ? '${_zone!['humidity_avg_6h']}%' : '--%', LucideIcons.cloudRain, AppColors.primary),
        _buildSensorTile('ETc', _zone?['etc'] != null ? '${_zone!['etc']} mm/h' : '0.84 mm/h', LucideIcons.wind, AppColors.accentPurple),
      ],
    );
  }

  Widget _buildSensorTile(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: color.withValues(alpha: 0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: color, size: 18),
          ),
          const Spacer(),
          Text(label, style: AppTextStyles.caption.copyWith(fontSize: 10, fontWeight: FontWeight.bold, color: color.withValues(alpha: 0.8))),
          Text(value, style: AppTextStyles.dataValue.copyWith(fontSize: 22, color: AppColors.textPrimary)),
        ],
      ),
    );
  }

  Widget _buildActionGrid() {
    return Column(
      children: [
        _buildFeatureAction(LucideIcons.dna, 'Biological Intelligence', 'VPD, ETc, and Thermal stress analysis', () => context.push('/zone/${widget.zoneId}/biology'), gradient: AppColors.healthGradient),
        const SizedBox(height: 12),
        _buildFeatureAction(LucideIcons.calendarDays, 'Growth Stage', 'Track Tillering → Panicle Initiation', () => context.push('/stage/${widget.zoneId}'), gradient: AppColors.bioGradient),
        const SizedBox(height: 12),
        _buildFeatureAction(LucideIcons.toggleRight, 'Manual Control', 'Override AI valve state', () => context.push('/control'), gradient: AppColors.aiGradient),
      ],
    );
  }

  Widget _buildFeatureAction(IconData icon, String title, String sub, VoidCallback onTap, {LinearGradient? gradient}) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppColors.border),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.02),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                gradient: gradient ?? AppColors.primaryGradient,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: Colors.white, size: 22),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: AppTextStyles.label.copyWith(fontWeight: FontWeight.bold)),
                  Text(sub, style: AppTextStyles.bodySmall),
                ],
              ),
            ),
            const Icon(LucideIcons.chevronRight, size: 18, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }

  Widget _buildNodeList() {
    final List<dynamic> nodes = _zone?['nodes'] ?? [];
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('AVAILABLE NODES', style: AppTextStyles.sectionLabel),
            if (nodes.isNotEmpty)
              Text('${nodes.length} Total', style: AppTextStyles.caption),
          ],
        ),
        const SizedBox(height: 16),
        if (nodes.isEmpty)
          Container(
            padding: const EdgeInsets.all(24),
            width: double.infinity,
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: AppColors.border)),
            child: Column(
              children: [
                Icon(LucideIcons.cpu, color: AppColors.textMuted.withValues(alpha: 0.3), size: 40),
                const SizedBox(height: 12),
                Text('No nodes paired yet', style: AppTextStyles.bodySmall),
              ],
            ),
          )
        else
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: nodes.length,
            separatorBuilder: (c, i) => const SizedBox(height: 12),
            itemBuilder: (c, i) => _buildNodeItem(nodes[i]),
          ),
      ],
    );
  }

  Widget _buildNodeItem(Map<String, dynamic> node) {
    final bool isOnline = node['status'] == 'online' || node['status'] == 'active';
    final double battery = (node['battery_pct'] ?? 0.0).toDouble();
    
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20), border: Border.all(color: AppColors.border)),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: isOnline ? AppColors.accentGreen.withValues(alpha: 0.1) : AppColors.background, borderRadius: BorderRadius.circular(12)),
            child: Icon(LucideIcons.radio, color: isOnline ? AppColors.accentGreen : AppColors.textMuted, size: 20),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(node['node_label'] ?? 'Sensor Node', style: AppTextStyles.label),
                Row(
                  children: [
                    if (node['current_moisture'] != null) ...[
                      const Icon(LucideIcons.droplet, size: 12, color: AppColors.primary),
                      const SizedBox(width: 4),
                      Text('${node['current_moisture'] ?? 0}%', style: AppTextStyles.caption.copyWith(color: AppColors.primary, fontWeight: FontWeight.bold)),
                      const SizedBox(width: 12),
                    ],
                    if (node['temperature'] != null) ...[
                      const Icon(LucideIcons.thermometer, size: 12, color: AppColors.accentOrange),
                      const SizedBox(width: 4),
                      Text('${node['temperature']}°C', style: AppTextStyles.caption.copyWith(color: AppColors.accentOrange)),
                    ],
                  ],
                ),
                Text(node['mac_address'] ?? 'Unknown MAC', style: AppTextStyles.caption.copyWith(fontSize: 10)),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Row(
                children: [
                  Icon(battery > 20 ? LucideIcons.batteryMedium : LucideIcons.batteryLow, size: 14, color: battery > 20 ? AppColors.accentGreen : AppColors.accentRed),
                  const SizedBox(width: 4),
                  Text('${battery.toInt()}%', style: AppTextStyles.caption.copyWith(fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(height: 8),
              GestureDetector(
                onTap: () => _handleManualIrrigate('irrigate', nodeSlotId: node['node_slot_id']),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: isOnline ? AppColors.primary : AppColors.textMuted.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'IRRIGATE',
                    style: AppTextStyles.caption.copyWith(
                      color: isOnline ? Colors.white : AppColors.textMuted,
                      fontWeight: FontWeight.bold,
                      fontSize: 10,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
