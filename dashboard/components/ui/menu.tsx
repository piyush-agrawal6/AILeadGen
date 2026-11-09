"use client";
import * as Menu from '@radix-ui/react-dropdown-menu';
import {cn} from '@/lib/utils';
export {Menu};
export function MenuContent({className,...props}:React.ComponentProps<typeof Menu.Content>){return <Menu.Portal><Menu.Content sideOffset={8} collisionPadding={12} className={cn('app-menu',className)} {...props}/></Menu.Portal>}
