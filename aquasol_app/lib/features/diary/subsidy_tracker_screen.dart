import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:intl/intl.dart';
import '../../core/services/api_service.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text_styles.dart';
import '../../shared/widgets/animated_interactive_card.dart';

class SubsidyTrackerScreen extends StatefulWidget {
  const SubsidyTrackerScreen({super.key});

  @override
  State<SubsidyTrackerScreen> createState() => _SubsidyTrackerScreenState();
}

class _SubsidyTrackerScreenState extends State<SubsidyTrackerScreen> {
  final _apiService = ApiService();
  bool _isLoading = true;
  List<dynamic> _subsidyEntries = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _isLoading = true);
    try {
      final entries = await _apiService.getDiary();
      if (mounted) {
        setState(() {
          // Filter for subsidy relevant entries
          _subsidyEntries = entries.where((e) => e['is_subsidy_relevant'] == true).toList();
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _submitClaim(String entryId) async {
    setState(() => _isLoading = true);
    final res = await _apiService.submitSubsidyClaim(entryId);
    if (res != null && res['status'] == 'success') {
      await _load();
    } else {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to submit claim.')),
        );
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
        title: Text('Subsidy Tracker', style: AppTextStyles.screenTitle),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _subsidyEntries.isEmpty
              ? _buildEmptyState()
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    itemCount: _subsidyEntries.length,
                    itemBuilder: (context, index) {
                      return _buildSubsidyCard(_subsidyEntries[index]);
                    },
                  ),
                ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(LucideIcons.landmark, size: 64, color: AppColors.textMuted.withValues(alpha: 0.3)),
          const SizedBox(height: 16),
          Text('No subsidy claims found.', style: AppTextStyles.label.copyWith(color: AppColors.textMuted)),
          const SizedBox(height: 8),
          Text('Log activities as "Subsidy Relevant" to track them here.', style: AppTextStyles.bodySmall, textAlign: TextAlign.center),
        ],
      ),
    );
  }

  Widget _buildSubsidyCard(Map<String, dynamic> entry) {
    final String status = entry['subsidy_status'] ?? '';
    final DateTime submittedDate = DateTime.parse(entry['timestamp']);
    
    // Estimate payout date (approx 45 days after submission)
    final DateTime estimatedPayout = submittedDate.add(const Duration(days: 45));
    final int daysRemaining = estimatedPayout.difference(DateTime.now()).inDays;
    
    Color statusColor;
    IconData statusIcon;
    
    switch (status.toLowerCase()) {
      case 'paid':
        statusColor = AppColors.accentGreen;
        statusIcon = LucideIcons.checkCircle2;
        break;
      case 'approved':
        statusColor = AppColors.accentBlue;
        statusIcon = LucideIcons.thumbsUp;
        break;
      case 'pending':
        statusColor = AppColors.accentOrange;
        statusIcon = LucideIcons.clock;
        break;
      default:
        statusColor = AppColors.textMuted;
        statusIcon = LucideIcons.fileEdit;
    }

    return AnimatedInteractiveCard(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      borderRadius: 24,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  children: [
                    Icon(statusIcon, color: statusColor, size: 14),
                    const SizedBox(width: 6),
                    Text(
                      status.isEmpty ? 'DRAFT' : status.toUpperCase(),
                      style: AppTextStyles.caption.copyWith(color: statusColor, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
              Text(
                'ID: ${entry['id'].substring(0, 8)}',
                style: AppTextStyles.caption.copyWith(fontFamily: 'monospace'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(entry['title'] ?? 'Subsidy Claim', style: AppTextStyles.cardTitle),
          const SizedBox(height: 8),
          Text(entry['description'] ?? '', style: AppTextStyles.bodySmall),
          const SizedBox(height: 20),
          const Divider(),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('SUBMITTED', style: AppTextStyles.caption.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(DateFormat('MMM dd, yyyy').format(submittedDate), style: AppTextStyles.label),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('EST. PAYOUT', style: AppTextStyles.caption.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(DateFormat('MMM dd, yyyy').format(estimatedPayout), style: AppTextStyles.label),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (status.toLowerCase() != 'paid') ...[
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: (45 - daysRemaining).clamp(0, 45) / 45.0,
                minHeight: 8,
                backgroundColor: const Color(0xFFF1F5F9),
                valueColor: AlwaysStoppedAnimation<Color>(statusColor),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(LucideIcons.timer, size: 14, color: AppColors.textSecondary),
                const SizedBox(width: 6),
                Text(
                  daysRemaining > 0 ? '$daysRemaining days pending for money' : 'Processing payout...',
                  style: AppTextStyles.caption.copyWith(color: AppColors.textPrimary, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ] else ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.accentGreen.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(LucideIcons.banknote, color: AppColors.accentGreen, size: 18),
                  const SizedBox(width: 8),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Text('Funds Transferred to Bank', style: AppTextStyles.label.copyWith(color: AppColors.accentGreen)),
                      if (entry['payment_reference'] != null)
                        Text('Ref: ${entry['payment_reference']}', style: AppTextStyles.caption.copyWith(color: AppColors.accentGreen.withValues(alpha: 0.7), fontFamily: 'monospace')),
                    ],
                  ),
                ],
              ),
            ),
          ],
          if (status.isEmpty || status.toLowerCase() == 'draft' || status.toLowerCase() == 'none') ...[
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: () => _submitClaim(entry['id']),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 0,
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(LucideIcons.send, size: 16),
                    SizedBox(width: 8),
                    Text('Submit for Subsidy', style: TextStyle(fontWeight: FontWeight.bold)),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
