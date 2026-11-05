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
  status: "confirmed" | "booked" | "completed" | "cancelled" | "rescheduled";
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
  virtualNumber: "09513886363",
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

export const MOCK_CALLS: CallRecord[] = [];

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
