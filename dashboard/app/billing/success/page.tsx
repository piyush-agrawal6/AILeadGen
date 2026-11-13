import Link from 'next/link';
export default function Pending(){return <section className="settings-page"><h1>Test checkout returned</h1><p>A successful redirect is not proof of payment. Billing shows the independently verified Razorpay status and settled period when available.</p><Link className="control" href="/billing">View verified billing status</Link></section>;}
