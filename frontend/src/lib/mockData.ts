export interface CallRecord {
  id: string;
  callerNumber: string;
  patientName: string;
  patientNameMl?: string;
  language: "ml-IN" | "en-IN";
  durationSec: number;
  outcome: "Booked" | "Rescheduled" | "Callback Created" | "Emergency Escalated" | "Inquiry Answered";
  timestamp: string;
  consentGiven: boolean;
  recordingKey?: string;
  summary: string;
  transcript: Array<{ speaker: "Agent" | "Caller"; text: string }>;
}

export interface AppointmentRecord {
  id: string;
  patientName: string;
  patientPhone: string;
  doctorName: string;
  treatmentName: string;
  timeStr: string;
  dateStr: string;
  status: "confirmed" | "completed" | "cancelled" | "rescheduled";
  visitType: string;
}

export interface CallbackTaskItem {
  id: string;
  patientName: string;
  phone: string;
  reason: string;
  preferredTime: string;
  status: "open" | "in_progress" | "resolved";
  createdAt: string;
}

export interface DoctorItem {
  id: string;
  name: string;
  qualification: string;
  specialties: string[];
  workingHours: string;
  active: boolean;
}

export interface FaqItem {
  id: string;
  question: string;
  questionMl: string;
  answer: string;
  answerMl: string;
  category: string;
}

export const MOCK_CLINIC = {
  name: "Sreerudra Ayurveda Hospital & Research Centre",
  location: "Alappuzha, Kerala",
  phone: "+91 477 225 1234",
  virtualNumber: "+91 98765 00001",
  status: "Agent Live & Answering",
  todayCallsCount: 28,
  todayAppointmentsCount: 14,
  pendingCallbacksCount: 3,
  agentAccuracy: 98.4,
};

export const MOCK_APPOINTMENTS: AppointmentRecord[] = [
  {
    id: "apt-101",
    patientName: "Ananthakrishnan Nair",
    patientPhone: "+91 98765 43210",
    doctorName: "Dr. Manoj Kumar (BAMS)",
    treatmentName: "Panchakarma Consultation",
    timeStr: "09:30 AM",
    dateStr: "Today",
    status: "confirmed",
    visitType: "In-Person",
  },
  {
    id: "apt-102",
    patientName: "Lakshmi Priya",
    patientPhone: "+91 94470 12345",
    doctorName: "Dr. Sreedevi K (MD Ayur)",
    treatmentName: "Shirodhara Therapy",
    timeStr: "10:15 AM",
    dateStr: "Today",
    status: "confirmed",
    visitType: "In-Person",
  },
  {
    id: "apt-103",
    patientName: "Rahul Varma",
    patientPhone: "+91 98951 88888",
    doctorName: "Dr. Manoj Kumar (BAMS)",
    treatmentName: "Spine & Joint Care Consultation",
    timeStr: "11:00 AM",
    dateStr: "Today",
    status: "rescheduled",
    visitType: "In-Person",
  },
  {
    id: "apt-104",
    patientName: "Geetha Menon",
    patientPhone: "+91 97455 66778",
    doctorName: "Dr. Sreedevi K (MD Ayur)",
    treatmentName: "Abhyangam Therapy",
    timeStr: "02:30 PM",
    dateStr: "Today",
    status: "confirmed",
    visitType: "In-Person",
  },
];

export const MOCK_CALLS: CallRecord[] = [
  {
    id: "call-901",
    callerNumber: "+91 98765 43210",
    patientName: "Ananthakrishnan Nair",
    patientNameMl: "അനന്തകൃഷ്ണൻ നായർ",
    language: "ml-IN",
    durationSec: 84,
    outcome: "Booked",
    timestamp: "10 minutes ago",
    consentGiven: true,
    recordingKey: "sreerudra/2026/10/call-901.wav",
    summary: "Patient inquired about knee joint pain. Booked consultation with Dr. Manoj for tomorrow 9:30 AM after confirmation readback.",
    transcript: [
      { speaker: "Agent", text: "നമസ്കാരം! ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിലേക്ക് സ്വാഗതം. ഞാൻ ഒരു എ.ഐ അസിസ്റ്റന്റ് ആണ്. സേവന നിലവാരം ഉറപ്പുവരുത്തുന്നതിനായി ഈ കോൾ റെക്കോർഡ് ചെയ്തോട്ടെ?" },
      { speaker: "Caller", text: "അതെ റെക്കോർഡ് ചെയ്തോളൂ. നാളെ ഡോക്ടർ മനോജിന് കാണാൻ സമയം ഉണ്ടോ?" },
      { speaker: "Agent", text: "ഡോക്ടർ മനോജ് നാളെ രാവിലെ ഒൻപത് മുപ്പതിനും വൈകുന്നേരം നാല് മണിക്കും ലഭ്യമാണ്. ഏത് സമയമാണ് താങ്കൾക്ക് സൗകര്യം?" },
      { speaker: "Caller", text: "രാവിലെ ഒൻപത് മുപ്പത് ആവട്ടെ." },
      { speaker: "Agent", text: "ശരി. താങ്കളുടെ വിവരങ്ങൾ ഞാൻ വായിക്കാം: പേര് അനന്തകൃഷ്ണൻ നായർ, ഫോൺ നമ്പർ ഒൻപത് എട്ട് ഏഴ് ആറ് അഞ്ച് നാല് മൂന്ന് രണ്ട് ഒന്ന് പൂജ്യം. ബുക്കിംഗ് സ്ഥിരീകരിക്കട്ടെ?" },
      { speaker: "Caller", text: "അതെ ശരിയാണ്, സ്ഥിരീകരിച്ചോളൂ." },
      { speaker: "Agent", text: "താങ്കളുടെ അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്തിരിക്കുന്നു. എസ്.എം.എസ് അയച്ചിട്ടുണ്ട്. നന്ദി!" },
    ],
  },
  {
    id: "call-902",
    callerNumber: "+91 94470 55555",
    patientName: "Thomas Mathew",
    language: "en-IN",
    durationSec: 62,
    outcome: "Inquiry Answered",
    timestamp: "32 minutes ago",
    consentGiven: true,
    recordingKey: "sreerudra/2026/10/call-902.wav",
    summary: "Caller asked for Panchakarma treatment packages and hospital location near Alappuzha boat jetty.",
    transcript: [
      { speaker: "Agent", text: "Hello! Welcome to Sreerudra Ayurveda Hospital. How can I assist you today?" },
      { speaker: "Caller", text: "Hi, do you offer 7-day Panchakarma packages, and where are you located?" },
      { speaker: "Agent", text: "Yes, we offer specialized 7-day, 14-day, and 21-day authentic Panchakarma packages. We are located near Cullen Road, Alappuzha. Would you like to consult our doctor?" },
      { speaker: "Caller", text: "Okay, I will discuss with my family and call back. Thank you." },
    ],
  },
  {
    id: "call-903",
    callerNumber: "+91 98951 22334",
    patientName: "Sujatha K",
    patientNameMl: "സുജാത കെ",
    language: "ml-IN",
    durationSec: 45,
    outcome: "Callback Created",
    timestamp: "1 hour ago",
    consentGiven: false,
    summary: "Caller asked for room tariff for inpatient rejuvenation therapy. Transferred to reception desk callback.",
    transcript: [
      { speaker: "Agent", text: "നമസ്കാരം! ശ്രീരുദ്ര ആയുർവേദ ഹോസ്പിറ്റലിലേക്ക് സ്വാഗതം. ഈ കോൾ റെക്കോർഡ് ചെയ്തോട്ടെ?" },
      { speaker: "Caller", text: "റെക്കോർഡിങ് വേണ്ട. ഐ.പി റൂം വാടക എത്രയാണെന്ന് അറിയാൻ വിളിച്ചതാണ്." },
      { speaker: "Agent", text: "തീർച്ചയായും. ഐ.പി അഡ്മിഷൻ സംബന്ധിച്ച കൃത്യമായ വിവരങ്ങൾ നൽകാൻ ഞാൻ ഞങ്ങളുടെ ഫ്രണ്ട് ഡെസ്ക് സ്റ്റാഫിനോട് താങ്കളെ തിരികെ വിളിക്കാൻ പറയാം." },
    ],
  },
];

export const MOCK_CALLBACKS: CallbackTaskItem[] = [
  {
    id: "task-01",
    patientName: "Sujatha K",
    phone: "+91 98951 22334",
    reason: "Inpatient (IP) AC/Non-AC Room tariff inquiry",
    preferredTime: "Today Afternoon",
    status: "open",
    createdAt: "1 hour ago",
  },
  {
    id: "task-02",
    patientName: "Pradeep Cherthala",
    phone: "+91 94960 99999",
    reason: "Requested callback regarding insurance reimbursement for Panchakarma",
    preferredTime: "Evening 4:00 PM",
    status: "open",
    createdAt: "2 hours ago",
  },
];

export const MOCK_DOCTORS: DoctorItem[] = [
  {
    id: "doc-1",
    name: "Dr. Manoj Kumar",
    qualification: "BAMS, Chief Ayurveda Consultant",
    specialties: ["Spine & Joint Disorders", "Rheumatology", "Post-Stroke Rehab"],
    workingHours: "Mon - Sat: 09:00 AM - 01:00 PM & 04:00 PM - 07:00 PM",
    active: true,
  },
  {
    id: "doc-2",
    name: "Dr. Sreedevi K",
    qualification: "BAMS, MD (Ayurveda Panchakarma)",
    specialties: ["Panchakarma Detox", "Stress & Insomnia", "Skin & Psoriasis"],
    workingHours: "Mon - Fri: 10:00 AM - 04:00 PM",
    active: true,
  },
];

export const MOCK_FAQS: FaqItem[] = [
  {
    id: "faq-1",
    question: "What are the hospital working hours?",
    questionMl: "ആശുപത്രി പ്രവർത്തിക്കുന്ന സമയം എപ്പോഴൊക്കെയാണ്?",
    answer: "Outpatient consultations are open Monday to Saturday from 9:00 AM to 7:00 PM. Sunday is open for emergency treatments.",
    answerMl: "തിങ്കൾ മുതൽ ശനി വരെ രാവിലെ 9 മണി മുതൽ വൈകുന്നേരം 7 മണി വരെ ഒ.പി പ്രവർത്തിക്കുന്നു. ഞായറാഴ്ച അത്യാഹിത ചികിത്സകൾ ലഭ്യമാണ്.",
    category: "General",
  },
  {
    id: "faq-2",
    question: "Do you have cashless insurance facility?",
    questionMl: "ഇൻഷുറൻസ് ക്ലെയിം സൗകര്യം ഇവിടെ ലഭ്യമാണോ?",
    answer: "Yes, we support reimbursement assistance for all major health insurance providers for admitted inpatient treatments.",
    answerMl: "അതെ, ഐ.പി അഡ്മിഷൻ ചികിത്സകൾക്ക് ഇൻഷുറൻസ് റീഇംബേഴ്സ്മെന്റ് രേഖകൾ കൃത്യമായി നൽകുന്നതാണ്.",
    category: "Billing",
  },
];
