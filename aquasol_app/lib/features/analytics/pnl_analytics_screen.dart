import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:lucide_icons/lucide_icons.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/services/api_service.dart';

class PnlAnalyticsScreen extends StatefulWidget {
  const PnlAnalyticsScreen({super.key});

  @override
  State<PnlAnalyticsScreen> createState() => _PnlAnalyticsScreenState();
}

class _PnlAnalyticsScreenState extends State<PnlAnalyticsScreen> {
  final _apiService = ApiService();
  bool _isLoading = true;
  Map<String, dynamic>? _pnlData;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final data = await _apiService.getPnlAnalytics();
      if (mounted) {
        setState(() {
          _pnlData = data;
        });
      }
    } catch (e) {
      debugPrint('PnL load error: $e');
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
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        leading: IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(LucideIcons.chevronLeft, color: AppColors.textPrimary),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('P&L Analytics', style: AppTextStyles.sectionLabel),
            Text(_pnlData?['farm_name'] ?? 'Loading...', style: AppTextStyles.caption),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 24),
                    _buildSeasonProfitCard(),
                    const SizedBox(height: 32),
                    Text('COST BREAKDOWN', style: AppTextStyles.caption.copyWith(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
                    const SizedBox(height: 16),
                    _buildCostDonutChart(),
                    const SizedBox(height: 32),
                    Text('ZONE ROI', style: AppTextStyles.caption.copyWith(fontWeight: FontWeight.bold, letterSpacing: 1.5)),
                    const SizedBox(height: 16),
                    if (_pnlData?['zone_roi'] != null)
                      ...(_pnlData!['zone_roi'] as List).map((z) => _buildZoneRoiItem(
                            z['name'],
                            (z['roi'] ?? 0.0) / 100.0,
                            '₹${z['profit']}',
                            _getColorForIndex(_pnlData!['zone_roi'].indexOf(z)),
                          )),
                    const SizedBox(height: 40),
                  ],
                ),
              ),
            ),
    );
  }

  Color _getColorForIndex(int i) {
    final colors = [AppColors.primary, AppColors.accentBlue, AppColors.accentOrange, AppColors.accentPurple];
    return colors[i % colors.length];
  }

  Widget _buildSeasonProfitCard() {
    final profit = _pnlData?['total_profit'] ?? 0;
    final growth = _pnlData?['growth_percent'] ?? 0;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        gradient: AppColors.pnlGradient,
        borderRadius: BorderRadius.circular(32),
        boxShadow: [
          BoxShadow(
            color: AppColors.accentOrange.withValues(alpha: 0.2),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('SEASON P&L', style: AppTextStyles.label.copyWith(color: Colors.white, fontSize: 16, letterSpacing: 1.5)),
              const Icon(LucideIcons.trendingUp, color: Colors.white, size: 28),
            ],
          ),
          const SizedBox(height: 20),
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text('₹$profit', style: AppTextStyles.dataDisplay.copyWith(color: Colors.white, fontSize: 48)),
              const SizedBox(width: 12),
              Text('Net Profit', style: AppTextStyles.label.copyWith(color: Colors.white.withValues(alpha: 0.7))),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Estimated profit up $growth% from last season. Main drivers: water efficiency & optimized fertilizer use.',
            style: AppTextStyles.bodyMedium.copyWith(color: Colors.white.withValues(alpha: 0.9)),
          ),
        ],
      ),
    );
  }

  Widget _buildCostDonutChart() {
    final breakdown = _pnlData?['cost_breakdown'] as Map<String, dynamic>? ?? {};
    if (breakdown.isEmpty) return const SizedBox();

    final sections = breakdown.entries.map((e) {
      return PieChartSectionData(
        color: _getColorForIndex(breakdown.keys.toList().indexOf(e.key)),
        value: (e.value as num).toDouble(),
        radius: 12,
        showTitle: false,
      );
    }).toList();

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            height: 140,
            child: PieChart(
              PieChartData(
                sectionsSpace: 4,
                centerSpaceRadius: 40,
                sections: sections,
              ),
            ),
          ),
          const SizedBox(width: 24),
          Expanded(
            child: Column(
              children: breakdown.entries.map((e) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _buildLegendItem(
                    e.key.toUpperCase(),
                    _getColorForIndex(breakdown.keys.toList().indexOf(e.key)),
                    '${e.value}%',
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(String label, Color color, String percent) {
    return Row(
      children: [
        Container(width: 8, height: 8, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 8),
        Expanded(child: Text(label, style: AppTextStyles.bodySmall)),
        Text(percent, style: AppTextStyles.label.copyWith(fontSize: 12)),
      ],
    );
  }

  Widget _buildZoneRoiItem(String name, double progress, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(name, style: AppTextStyles.bodyMedium.copyWith(color: AppColors.textPrimary)),
              Text(value, style: AppTextStyles.label.copyWith(color: color)),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress.clamp(0.0, 1.0),
              minHeight: 8,
              backgroundColor: const Color(0xFFF1F5F9),
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
        ],
      ),
    );
  }
}
