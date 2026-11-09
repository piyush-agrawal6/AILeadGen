import 'server-only';
import {currentUser} from './session';
import {serverEnv} from './env';
/** Opt-in archive only; the backend separately verifies organization and role. */
export async function canViewLegacyArchive(){
 if(process.env.HEYSOW_INTERNAL_EXPERIMENTS_ENABLED!=='true')return false;
 const user=await currentUser();return Boolean(user?.email&&user.email===serverEnv().allowed[0]);
}
