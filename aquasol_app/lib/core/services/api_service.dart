import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // Use localhost for Flutter Web (browser), LAN IP for mobile/desktop
  static String get baseUrl {
    // Secure public tunnel URL for local backend
    return 'https://3960dba9dd0249.lhr.life/api/v1/';
  }

  final Dio _dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
  ));

  Dio get dio => _dio;

  ApiService() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final prefs = await SharedPreferences.getInstance();
        final token = prefs.getString('access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
    ));
  }

  Future<List<dynamic>> getUnassignedDevices() async {
    try {
      final response = await _dio.get('unassigned');
      if (response.statusCode == 200) return response.data;
    } catch (e) {
      debugPrint('GetUnassignedDevices error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> assignDevice({
    String? deviceId,
    String? mac,
    required String farmId,
    String? acreId,
    String? zoneId,
    String? nodeName,
    String? acreName,
    String? zoneName,
  }) async {
    try {
      final response = await _dio.post('assign', data: {
        if (deviceId != null) 'device_id': deviceId,
        if (mac != null) 'mac': mac,
        'farm_id': farmId,
        'acre_id': acreId,
        'zone_id': zoneId,
        'node_name': nodeName,
        'acre_name': acreName,
        'zone_name': zoneName,
      });
      return response.data;
    } catch (e) {
      debugPrint('AssignDevice error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> assignDeviceByCode({
    required String pairingCode,
    required String farmId,
    String? zoneId,
    String? nodeSlotId,
    String? nodeName,
    bool isMaster = false,
  }) async {
    try {
      final response = await _dio.post('assign/code', data: {
        'pairing_code': pairingCode,
        'farm_id': farmId,
        'zone_id': zoneId,
        'node_slot_id': nodeSlotId,
        'node_name': nodeName,
        'is_master': isMaster,
      });
      return response.data;
    } catch (e) {
      debugPrint('AssignDeviceByCode error: $e');
      return null;
    }
  }



  // ─── Auth & Profile ───────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> login(String identifier, String password) async {
    try {
      final response = await _dio.post('auth/login', data: {
        'identifier': identifier,
        'password': password,
      });
      if (response.statusCode == 200) {
        final data = response.data;
        await _saveToken(data['access_token']);
        return data;
      }
      return null;
    } catch (e) {
      debugPrint('Login error: $e');
      rethrow;
    }
  }

  Future<bool> updateLanguagePreference(String userId, String lang) async {
    try {
      final response = await _dio.patch('auth/preference/$userId', data: {
        'preferred_lang': lang,
      });
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('UpdateLanguagePreference error: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> register({
    required String name,
    required String phone,
    String? email,
    required String password,
  }) async {
    try {
      final response = await _dio.post('auth/register', data: {
        'name': name,
        'phone': phone,
        'email': email,
        'password': password,
        'confirm_password': password,
      });
      if (response.statusCode == 201) {
        final data = response.data;
        await _saveToken(data['access_token']);
        return data;
      }
      return null;
    } catch (e) {
      debugPrint('Register error: $e');
      rethrow;
    }
  }

  Future<Map<String, dynamic>?> getMe() async {
    try {
      final response = await _dio.get('auth/me');
      if (response.statusCode == 200) return response.data;
      return null;
    } catch (e) {
      debugPrint('GetMe error: $e');
      rethrow;
    }
  }

  // ─── Farm & Zones ─────────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> createFarm({
    required String name,
    String? location,
    int? totalAcres,
    String? waterSource,
  }) async {
    try {
      final response = await _dio.post('farms/farm', data: {
        'name': name,
        'location': location,
        'total_acres': totalAcres,
        'water_source': waterSource,
      });
      return response.data;
    } catch (e) {
      debugPrint('CreateFarm error: $e');
      rethrow; // Let caller handle auth errors
    }
  }

  Future<Map<String, dynamic>?> createZone({
    required String farmId,
    String? acreId,
    required String name,
    required String cropType,
    required String soilType,
    String? irrigationType,
    double? areaAcres,
    String? sowingDate,
    int? weeksSinceSowing,
    String? currentStage,
    int? nodeSlotsCount,
    List<Map<String, String>>? nodes,
  }) async {
    try {
      final response = await _dio.post('farms/zone', data: {
        'farm_id': farmId,
        'acre_id': acreId,
        'name': name,
        'crop_type': cropType,
        'soil_type': soilType,
        'irrigation_type': irrigationType,
        'area_acres': areaAcres,
        'sowing_date': sowingDate,
        'weeks_since_sowing': weeksSinceSowing,
        'current_stage': currentStage,
        'node_slots_count': nodeSlotsCount,
        'nodes': nodes ?? [],
      });
      return response.data;
    } catch (e) {
      debugPrint('CreateZone error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> addNodeSlot({required String zoneId, required String name}) async {
    try {
      final response = await _dio.post('farms/node_slot', data: {'zone_id': zoneId, 'name': name});
      return response.data;
    } catch (e) {
      debugPrint('AddNodeSlot error: $e');
      return null;
    }
  }

  Future<bool> deleteNodeSlot(String slotId) async {
    try {
      final response = await _dio.delete('farms/node_slot/$slotId');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('DeleteNodeSlot error: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> getDashboard() async {
    try {
      final response = await _dio.get('dashboard');
      if (response.statusCode == 200) return response.data;
    } catch (e) {
      debugPrint('Dashboard error: $e');
    }
    return null;
  }


  Future<List<dynamic>> getZones() async {
    try {
      final response = await _dio.get('zones');
      if (response.statusCode == 200) return response.data;
    } catch (e) {
      debugPrint('GetZones error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> getZone(String zoneId) async {
    try {
      final response = await _dio.get('/zones/$zoneId');
      if (response.statusCode == 200) return response.data;
    } catch (e) {
      debugPrint('GetZone error: $e');
    }
    return null;
  }

  Future<bool> updateZone(String zoneId, Map<String, dynamic> data) async {
    try {
      final response = await _dio.patch('/zones/$zoneId', data: data);
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('UpdateZone error: $e');
      return false;
    }
  }

  // ─── Control & Commands ───────────────────────────────────────────────────

  Future<Map<String, dynamic>?> manualOverride({
    required String zoneId,
    String? nodeSlotId,
    required String action,
    int durationMin = 15,
    String? reason,
  }) async {
    try {
      final response = await _dio.post('/control/override', data: {
        'zone_id': zoneId,
        'node_slot_id': nodeSlotId,
        'action': action,
        'duration_min': durationMin,
        'reason': reason,
      });
      return response.data;
    } catch (e) {
      debugPrint('ManualOverride error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> acreOverride({
    required String acreId,
    required String action,
    int durationMin = 15,
    String? reason,
  }) async {
    try {
      final response = await _dio.post('/acre_override', data: {
        'acre_id': acreId,
        'action': action,
        'duration_min': durationMin,
        'reason': reason,
      });
      return response.data;
    } catch (e) {
      debugPrint('AcreOverride error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> handleAdvisoryAction({
    required String zoneId,
    required String action,
    String? decisionId,
  }) async {
    try {
      final response = await _dio.post('/advisory-action', data: {
        'zone_id': zoneId,
        'action': action,
        'decision_id': decisionId,
      });
      return response.data;
    } catch (e) {
      debugPrint('AdvisoryAction error: $e');
      return null;
    }
  }

  Future<List<dynamic>> getSchedules() async {
    try {
      final response = await _dio.get('/schedules');
      if (response.statusCode == 200) return response.data;
    } catch (e) {
      debugPrint('GetSchedules error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> createSchedule({
    String? label,
    String? zoneId,
    String? acreId,
    required String time,
    required List<String> days,
    int durationMin = 30,
    int intensity = 80,
    String mode = 'manual',
    bool isActive = true,
  }) async {
    try {
      final response = await _dio.post('/schedules', data: {
        'label': label,
        'zone_id': zoneId,
        'acre_id': acreId,
        'time': time,
        'days': days,
        'duration_min': durationMin,
        'intensity': intensity,
        'mode': mode,
        'is_active': isActive,
      });
      return response.data;
    } catch (e) {
      debugPrint('CreateSchedule error: $e');
      return null;
    }
  }

  Future<bool> deleteSchedule(String scheduleId) async {
    try {
      final response = await _dio.delete('/schedules/$scheduleId');
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('DeleteSchedule error: $e');
      return false;
    }
  }

  // ─── Bio & Stage ──────────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> getBiology(String zoneId) async {
    try {
      final response = await _dio.get('zones/$zoneId/biology');
      if (response.statusCode == 200) return response.data;
    } catch (e) {
      debugPrint('Biology error: $e');
    }
    return null;
  }

  // ─── Diary & Reports ──────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> logActivity({
    required String zoneId,
    required String activityType,
    required String title,
    required String body,
    Map<String, dynamic>? metadata,
    bool isSubsidy = false,
  }) async {
    try {
      final response = await _dio.post('/activity', data: {
        'zone_id': zoneId,
        'activity_type': activityType,
        'title': title,
        'body': body,
        'metadata': metadata ?? {},
        'is_subsidy': isSubsidy,
      });
      return response.data;
    } catch (e) {
      debugPrint('LogActivity error: $e');
      return null;
    }
  }

  Future<List<dynamic>> getDiary() async {
    try {
      final response = await _dio.get('diary');
      if (response.statusCode == 200) return response.data['entries'];
    } catch (e) {
      debugPrint('GetDiary error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> getWaterUsage() async {
    try {
      final response = await _dio.get('water-usage');
      if (response.statusCode == 200) return response.data;
    } catch (e) {
      debugPrint('WaterUsage error: $e');
    }
    return null;
  }

  // ─── AI Chat & Planner ────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> chat(String message, {String? zoneId}) async {
    try {
      final response = await _dio.post('chat', data: {
        'message': message,
        'zone_id': zoneId,
      });
      return response.data;
    } catch (e) {
      debugPrint('Chat error: $e');
      return {'reply': 'I am having trouble connecting to my brain right now. Please try again later.'};
    }
  }

  Future<Map<String, dynamic>?> getCropPlan({
    required String query,
    required String zoneId,
    String? goal,
    double? budget,
    String mode = 'new_season',
  }) async {
    try {
      final response = await _dio.post('planner', data: {
        'query': query,
        'zone_id': zoneId,
        'farmer_goal': goal,
        'budget_inr_per_acre': budget,
        'mode': mode,
      });
      return response.data;
    } catch (e) {
      debugPrint('Planner error: $e');
      return null;
    }
  }

  Future<List<dynamic>> getSensorHistory({required String zoneId, int days = 7}) async {
    try {
      final response = await _dio.get('/sensors/history', queryParameters: {
        'zone_id': zoneId,
        'days': days,
      });
      return response.data;
    } catch (e) {
      debugPrint('GetSensorHistory error: $e');
      return [];
    }
  }

  Future<List<String>> listCrops() async {
    try {
      final response = await _dio.get('intelligence/crops');
      if (response.statusCode == 200) {
        return List<String>.from(response.data);
      }
    } catch (e) {
      debugPrint('ListCrops error: $e');
    }
    return [];
  }

  Future<Map<String, dynamic>?> getSetupHints(String crop) async {
    try {
      final response = await _dio.get('intelligence/setup-hints', queryParameters: {
        'crop': crop,
      });
      return response.data;
    } catch (e) {
      debugPrint('GetSetupHints error: $e');
      return null;
    }
  }

  // ─── Token Management ─────────────────────────────────────────────────────

  Future<void> _saveToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('access_token', token);
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('access_token');
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
  }

  // ─── Health & Analytics ───────────────────────────────────────────────────

  Future<List<dynamic>> getAlerts() async {
    try {
      final response = await _dio.get('alerts');
      return response.data;
    } catch (e) {
      debugPrint('GetAlerts error: $e');
      return [];
    }
  }

  Future<Map<String, dynamic>?> getSystemHealth() async {
    try {
      final response = await _dio.get('system-health');
      return response.data;
    } catch (e) {
      debugPrint('SystemHealth error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> getPredictions() async {
    try {
      final response = await _dio.get('predictions');
      return response.data;
    } catch (e) {
      debugPrint('Predictions error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> getPnlAnalytics() async {
    try {
      final response = await _dio.get('analytics/pnl');
      return response.data;
    } catch (e) {
      debugPrint('PnlAnalytics error: $e');
      return null;
    }
  }

  Future<Map<String, dynamic>?> updateProfile(Map<String, dynamic> data) async {
    try {
      final response = await _dio.put('auth/profile', data: data);
      return response.data;
    } catch (e) {
      debugPrint('UpdateProfile error: $e');
      return null;
    }
  }

  Future<bool> sendReportToGov(String reportId, String email) async {
    try {
      await _dio.post('reports/send', data: {'report_id': reportId, 'email': email});
      return true;
    } catch (e) {
      debugPrint('SendReport error: $e');
      return false;
    }
  }

  Future<Map<String, dynamic>?> submitSubsidyClaim(String entryId) async {
    try {
      final response = await _dio.post('subsidy/submit', queryParameters: {'entry_id': entryId});
      return response.data;
    } catch (e) {
      debugPrint('SubmitSubsidyClaim error: $e');
      return null;
    }
  }
}
