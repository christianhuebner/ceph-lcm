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

import * as _ from 'lodash';
import { inject, TestBed, ComponentFixture } from '@angular/core/testing';
import { APP_BASE_HREF } from '@angular/common';

import { HintsStep } from './hints';
import { AppModule } from '../../app.module';
import { BaseModel, Playbook, Hint } from '../../models';

import { DOMHelper } from '../../../testing/dom';
import globals = require('../../services/globals');

describe('Configuration wizard: hints step component', () => {
  let fixture: ComponentFixture<HintsStep>;
  let component: HintsStep;
  let mockData: any;
  let dom: DOMHelper;


  beforeEach(
    done => TestBed.configureTestingModule({
        imports: [AppModule],
        providers: [
          {provide: APP_BASE_HREF, useValue: '/'}
        ]
      })
      .compileComponents()
      .then(done)
  );

  beforeEach(() => {
    fixture = TestBed.createComponent(HintsStep);
    component = fixture.componentInstance;
    dom = new DOMHelper(fixture);
    component.model = new BaseModel({});
    component.init();
  });

  it('initializes itself and the model', () => {
    expect(component.selectedPlaybook).toBeNull();
    expect(component.model.data.hints).toEqual([]);
  });

  it('is not shown in the deck when playbook has no hints', () => {
    expect(component.isShownInDeck()).toBeFalsy();
  });

  it('is not shown in the deck for edited configurations', () => {
    component.model.id = 'Dummy ID';
    component.selectedPlaybook = new Playbook({hints: [1, 2, 3]});
    expect(component.isShownInDeck()).toBeFalsy();
  });

  it('listens for playbook selection changes', () => {
    let initSpy = spyOn(component, 'init');
    let dummyPlaybook = new Playbook({id: 'Dummy ID'});
    component.setSharedData('selectedPlaybook', dummyPlaybook);
    fixture.detectChanges();
    expect(initSpy).toHaveBeenCalled();
    expect(component.selectedPlaybook).toEqual(dummyPlaybook);
  });

  it('is valid when all hints values are', () => {
    component.hintsValidity = {'1': true, '2': true, '3': true};
    expect(component.isValid()).toBeTruthy();
    component.hintsValidity['4'] = false;
    expect(component.isValid()).toBeFalsy();
  });

  it('keeps hints values between the step switches', () => {
    let dummyId = 'id1';
    let dummyHint: Hint = {id: dummyId, default_value: 2};
    component.addHintValue(dummyHint);
    expect(dummyHint.value).toBe(2);
    component.registerHint({id: dummyId, value: 1, isValid: true});
    component.addHintValue(dummyHint);
    expect(dummyHint.value).toBe(1);
  });

});
