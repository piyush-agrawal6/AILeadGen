import Link from 'next/link';
export default function Cancelled(){return <section className="settings-page"><h1>Checkout closed</h1><p>No successful payment is assumed. Closing this page does not cancel an existing recurring mandate. Manage cancellation and check provider status in billing.</p><Link className="control" href="/billing">Return to billing</Link></section>;}
