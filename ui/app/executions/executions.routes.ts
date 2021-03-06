/**
* Copyright (c) 2016 Mirantis Inc.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*    http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
* implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/

import { Routes } from '@angular/router';
import { LoggedIn } from '../services/auth';
import { ExecutionsComponent, LogsComponent } from './index';

export const executionsRoutes: Routes = [
  {
    path: 'executions',
    component: ExecutionsComponent,
    canActivate: [LoggedIn],
    data: {restrictTo: [
      'create_execution',
      'view_execution',
      'view_execution_steps',
      'delete_execution'
    ]}
  },
  {
    path: 'executions/:execution_id',
    component: LogsComponent,
    canActivate: [LoggedIn],
    data: {restrictTo: [
      'view_execution_steps'
    ]}
  }
];
